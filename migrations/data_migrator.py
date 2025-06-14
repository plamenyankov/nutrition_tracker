import os
import sys
import sqlite3
import mysql.connector
import logging
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
import json
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from models.database.connection_manager import DatabaseConnectionManager
from config.environments import get_sqlite_source_path

logger = logging.getLogger(__name__)

class DataMigrator:
    """Tool to migrate data from SQLite to MySQL"""

    def __init__(self, source_sqlite_path: str = None, batch_size: int = 1000):
        self.sqlite_path = source_sqlite_path or get_sqlite_source_path()
        self.mysql_manager = DatabaseConnectionManager(use_mysql=True)
        self.batch_size = batch_size

        logger.info(f"Initializing data migrator")
        logger.info(f"Source SQLite: {self.sqlite_path}")
        logger.info(f"Target MySQL: {self.mysql_manager.config.database}")
        logger.info(f"Batch size: {self.batch_size}")

    def get_table_order(self) -> List[str]:
        """Get tables in dependency order for migration"""
        # This is a simplified version - in production, you'd want to
        # analyze foreign keys to determine proper order

        # Define migration order based on dependencies
        ordered_tables = [
            # Base tables (no foreign keys)
            'Unit',
            'Ingredient',
            'exercises',
            'users',

            # Tables with foreign keys to base tables
            'Nutrition',
            'Ingredient_Quantity',
            'Recipe',
            'workout_sessions',
            'Favorites',

            # Tables with multiple foreign keys
            'Recipe_Ingredients',
            'Consumption',
            'recipe_consumption',
            'workout_sets',
            'progression_history',

            # Monitoring and security tables
            'performance_metrics',
            'metrics',
            'alerts',
            'health_checks',
            'user_sessions',
            'failed_login_attempts',
            'audit_logs',
        ]

        # Get all tables from SQLite
        with sqlite3.connect(self.sqlite_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            all_tables = [row[0] for row in cursor.fetchall()]

        # Add any tables not in our ordered list
        for table in all_tables:
            if table not in ordered_tables:
                ordered_tables.append(table)

        # Filter to only existing tables
        existing_ordered_tables = [t for t in ordered_tables if t in all_tables]

        return existing_ordered_tables

    def migrate_table_data(self, table_name: str) -> Dict[str, Any]:
        """Migrate data for a single table"""
        result = {
            'table': table_name,
            'rows_migrated': 0,
            'success': True,
            'error': None,
            'start_time': datetime.now()
        }

        try:
            # Get SQLite data
            with sqlite3.connect(self.sqlite_path) as sqlite_conn:
                sqlite_conn.row_factory = sqlite3.Row
                cursor = sqlite_conn.cursor()

                # Get total row count
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                total_rows = cursor.fetchone()[0]
                logger.info(f"Migrating {total_rows} rows from table: {table_name}")

                if total_rows == 0:
                    result['end_time'] = datetime.now()
                    return result

                # Get all data from table
                cursor.execute(f"SELECT * FROM {table_name}")
                columns = [description[0] for description in cursor.description]

                # Process in batches
                rows_migrated = 0
                while True:
                    batch = cursor.fetchmany(self.batch_size)
                    if not batch:
                        break

                    # Prepare data for MySQL
                    batch_data = []
                    for row in batch:
                        row_data = []
                        for i, value in enumerate(row):
                            # Handle different data types
                            if value is None:
                                row_data.append(None)
                            elif isinstance(value, (int, float, str)):
                                row_data.append(value)
                            elif isinstance(value, bytes):
                                # Handle blob data
                                row_data.append(value)
                            else:
                                # Convert other types to string
                                row_data.append(str(value))
                        batch_data.append(tuple(row_data))

                    # Insert into MySQL
                    self._insert_batch_mysql(table_name, columns, batch_data)
                    rows_migrated += len(batch)

                    if rows_migrated % 10000 == 0:
                        logger.info(f"Progress: {rows_migrated}/{total_rows} rows migrated for {table_name}")

                result['rows_migrated'] = rows_migrated

        except Exception as e:
            logger.error(f"Failed to migrate table {table_name}: {e}")
            result['success'] = False
            result['error'] = str(e)

        result['end_time'] = datetime.now()
        result['duration'] = (result['end_time'] - result['start_time']).total_seconds()

        return result

    def _insert_batch_mysql(self, table_name: str, columns: List[str], data: List[Tuple]):
        """Insert a batch of data into MySQL"""
        if not data:
            return

        # Build insert query
        placeholders = ', '.join(['%s'] * len(columns))
        column_names = ', '.join([f'`{col}`' for col in columns])

        insert_query = f"""
            INSERT INTO `{table_name}` ({column_names})
            VALUES ({placeholders})
        """

        with self.mysql_manager.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.executemany(insert_query, data)
                conn.commit()
            except mysql.connector.Error as e:
                if "Duplicate entry" in str(e):
                    # Try inserting one by one to skip duplicates
                    logger.warning(f"Duplicate entries found in {table_name}, inserting individually")
                    for row in data:
                        try:
                            cursor.execute(insert_query, row)
                            conn.commit()
                        except mysql.connector.Error as e2:
                            if "Duplicate entry" not in str(e2):
                                logger.error(f"Failed to insert row: {e2}")
                else:
                    raise

    def migrate_all_data(self, tables: List[str] = None) -> Dict[str, Any]:
        """Migrate all tables in dependency order"""
        overall_result = {
            'start_time': datetime.now(),
            'tables': {},
            'total_rows': 0,
            'success': True
        }

        # Get tables to migrate
        tables_to_migrate = tables or self.get_table_order()

        logger.info(f"Starting data migration for {len(tables_to_migrate)} tables")

        # Disable foreign key checks during migration
        with self.mysql_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            conn.commit()

        try:
            # Migrate each table
            for table_name in tables_to_migrate:
                logger.info(f"\nMigrating table: {table_name}")
                result = self.migrate_table_data(table_name)
                overall_result['tables'][table_name] = result
                overall_result['total_rows'] += result['rows_migrated']

                if not result['success']:
                    overall_result['success'] = False
                    logger.error(f"Failed to migrate table {table_name}")
                    # Continue with other tables even if one fails

        finally:
            # Re-enable foreign key checks
            with self.mysql_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
                conn.commit()

        overall_result['end_time'] = datetime.now()
        overall_result['duration'] = (overall_result['end_time'] - overall_result['start_time']).total_seconds()

        # Log summary
        logger.info("\n" + "="*50)
        logger.info("MIGRATION SUMMARY")
        logger.info("="*50)
        logger.info(f"Total tables migrated: {len(overall_result['tables'])}")
        logger.info(f"Total rows migrated: {overall_result['total_rows']}")
        logger.info(f"Total duration: {overall_result['duration']:.2f} seconds")
        logger.info(f"Overall success: {overall_result['success']}")

        for table_name, result in overall_result['tables'].items():
            status = "✓" if result['success'] else "✗"
            logger.info(f"{status} {table_name}: {result['rows_migrated']} rows")
            if result.get('error'):
                logger.error(f"  Error: {result['error']}")

        return overall_result

    def verify_migration(self) -> Dict[str, Any]:
        """Verify data migration by comparing row counts"""
        verification_result = {
            'success': True,
            'tables': {},
            'discrepancies': []
        }

        try:
            # Get SQLite row counts
            sqlite_counts = {}
            with sqlite3.connect(self.sqlite_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
                tables = cursor.fetchall()

                for (table_name,) in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    sqlite_counts[table_name] = cursor.fetchone()[0]

            # Get MySQL row counts
            mysql_counts = {}
            with self.mysql_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()

                for (table_name,) in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
                    mysql_counts[table_name] = cursor.fetchone()[0]

            # Compare counts
            for table_name, sqlite_count in sqlite_counts.items():
                mysql_count = mysql_counts.get(table_name, 0)

                verification_result['tables'][table_name] = {
                    'sqlite_count': sqlite_count,
                    'mysql_count': mysql_count,
                    'match': sqlite_count == mysql_count
                }

                if sqlite_count != mysql_count:
                    discrepancy = f"{table_name}: SQLite={sqlite_count}, MySQL={mysql_count}"
                    verification_result['discrepancies'].append(discrepancy)
                    verification_result['success'] = False

            # Log verification results
            logger.info("\n" + "="*50)
            logger.info("MIGRATION VERIFICATION")
            logger.info("="*50)

            for table_name, counts in verification_result['tables'].items():
                status = "✓" if counts['match'] else "✗"
                logger.info(f"{status} {table_name}: SQLite={counts['sqlite_count']}, MySQL={counts['mysql_count']}")

            if verification_result['success']:
                logger.info("\n✓ All tables migrated successfully with matching row counts!")
            else:
                logger.warning(f"\n✗ Found {len(verification_result['discrepancies'])} discrepancies")
                for discrepancy in verification_result['discrepancies']:
                    logger.warning(f"  - {discrepancy}")

        except Exception as e:
            logger.error(f"Verification failed: {e}")
            verification_result['success'] = False
            verification_result['error'] = str(e)

        return verification_result

    def create_migration_report(self, migration_result: Dict[str, Any], verification_result: Dict[str, Any]) -> str:
        """Create a detailed migration report"""
        report_path = f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        report = {
            'migration_date': datetime.now().isoformat(),
            'source_database': self.sqlite_path,
            'target_database': {
                'host': self.mysql_manager.config.host,
                'database': self.mysql_manager.config.database
            },
            'migration_result': migration_result,
            'verification_result': verification_result
        }

        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"Migration report saved to: {report_path}")
        return report_path
