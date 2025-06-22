import os
import sys
import sqlite3
import mysql.connector
import logging
from typing import List, Dict, Any, Tuple
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from models.database.connection_manager import DatabaseConnectionManager
from models.database.connection_manager import get_db_manager, IS_PRODUCTION

logger = logging.getLogger(__name__)

class SchemaMigrator:
    """Tool to migrate schema from SQLite to MySQL"""

    def __init__(self, source_sqlite_path: str = None):
        self.sqlite_path = source_sqlite_path or get_sqlite_source_path()
        self.mysql_manager = get_db_manager()

        logger.info(f"Initializing schema migrator")
        logger.info(f"Source SQLite: {self.sqlite_path}")
        logger.info(f"Target MySQL: {self.mysql_manager.config.database} at {self.mysql_manager.config.host}")

    def extract_sqlite_schema(self) -> Dict[str, Any]:
        """Extract complete schema from SQLite database"""
        schema = {'tables': {}, 'indexes': [], 'views': []}

        try:
            with sqlite3.connect(self.sqlite_path) as conn:
                cursor = conn.cursor()

                # Get all tables
                cursor.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table'
                    AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                """)
                tables = cursor.fetchall()

                for (table_name,) in tables:
                    logger.info(f"Extracting schema for table: {table_name}")

                    # Get table schema
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = cursor.fetchall()

                    # Get foreign keys
                    cursor.execute(f"PRAGMA foreign_key_list({table_name})")
                    foreign_keys = cursor.fetchall()

                    # Get the CREATE TABLE statement
                    cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
                    create_sql = cursor.fetchone()[0]

                    schema['tables'][table_name] = {
                        'columns': columns,
                        'foreign_keys': foreign_keys,
                        'create_sql': create_sql
                    }

                # Get indexes
                cursor.execute("""
                    SELECT name, tbl_name, sql
                    FROM sqlite_master
                    WHERE type='index'
                    AND name NOT LIKE 'sqlite_%'
                    AND sql IS NOT NULL
                """)
                schema['indexes'] = cursor.fetchall()

                # Get views
                cursor.execute("""
                    SELECT name, sql
                    FROM sqlite_master
                    WHERE type='view'
                """)
                schema['views'] = cursor.fetchall()

        except sqlite3.Error as e:
            logger.error(f"Failed to extract SQLite schema: {e}")
            raise

        return schema

    def convert_sqlite_type_to_mysql(self, sqlite_type: str) -> str:
        """Convert SQLite data type to MySQL data type"""
        if not sqlite_type:
            return 'VARCHAR(255)'

        sqlite_type = sqlite_type.upper()

        # Type mapping
        type_mapping = {
            'INTEGER': 'INT',
            'INT': 'INT',
            'TINYINT': 'TINYINT',
            'SMALLINT': 'SMALLINT',
            'MEDIUMINT': 'MEDIUMINT',
            'BIGINT': 'BIGINT',
            'REAL': 'DOUBLE',
            'FLOAT': 'FLOAT',
            'DOUBLE': 'DOUBLE',
            'DECIMAL': 'DECIMAL(10,2)',
            'NUMERIC': 'NUMERIC(10,2)',
            'TEXT': 'TEXT',
            'BLOB': 'BLOB',
            'BOOLEAN': 'BOOLEAN',
            'BOOL': 'BOOLEAN',
            'DATE': 'DATE',
            'DATETIME': 'DATETIME',
            'TIMESTAMP': 'TIMESTAMP',
            'TIME': 'TIME',
            'VARCHAR': 'VARCHAR(255)',
            'CHAR': 'CHAR(255)',
            'CLOB': 'TEXT',
        }

        # Check for parameterized types like VARCHAR(n)
        for base_type, mysql_type in type_mapping.items():
            if sqlite_type.startswith(base_type):
                if '(' in sqlite_type and base_type in ['VARCHAR', 'CHAR', 'DECIMAL', 'NUMERIC']:
                    # Preserve the parameter
                    return sqlite_type.replace(base_type, mysql_type.split('(')[0])
                return mysql_type

        # Default fallback
        return 'VARCHAR(255)'

    def convert_sqlite_default_to_mysql(self, default_value: str, column_type: str) -> str:
        """Convert SQLite default value to MySQL equivalent"""
        if not default_value:
            return None

        # MySQL doesn't allow defaults for TEXT, BLOB, GEOMETRY, JSON columns
        if column_type.upper() in ['TEXT', 'BLOB', 'LONGTEXT', 'MEDIUMTEXT', 'TINYTEXT', 'JSON', 'GEOMETRY']:
            return None

        # Handle SQLite functions - MySQL doesn't allow most functions as defaults
        if "strftime(" in default_value.lower():
            # For date/time functions, we'll skip the default and handle in application
            return None

        # Handle 'now' function - MySQL doesn't allow NOW() as default for most columns
        if default_value.lower() in ["'now'", "now", "now()"]:
            # Only TIMESTAMP columns can have NOW() as default
            if column_type.upper() in ['TIMESTAMP']:
                return "CURRENT_TIMESTAMP"
            else:
                # For other date/time types, skip default
                return None

        # Handle CURRENT_TIMESTAMP variations
        if default_value.upper() in ['CURRENT_TIMESTAMP', "'CURRENT_TIMESTAMP'"]:
            if column_type.upper() in ['TIMESTAMP']:
                return "CURRENT_TIMESTAMP"
            else:
                return None

        # Handle boolean values
        if default_value.upper() in ['TRUE', 'FALSE']:
            return default_value.upper()

        # Handle numeric values
        if default_value.replace('-', '').replace('.', '').isdigit():
            return default_value

        # Handle quoted strings - remove extra quotes
        if default_value.startswith("'") and default_value.endswith("'"):
            # Remove outer quotes and escape inner quotes
            inner_value = default_value[1:-1].replace("'", "\\'")
            # Don't add quotes around function names
            if inner_value.upper() in ['CURRENT_TIMESTAMP', 'NOW', 'CURDATE', 'CURTIME']:
                return inner_value.upper() if column_type.upper() == 'TIMESTAMP' else None
            return f"'{inner_value}'"

        # Handle double-quoted strings
        if default_value.startswith('"') and default_value.endswith('"'):
            inner_value = default_value[1:-1].replace("'", "\\'")
            # Don't add quotes around function names
            if inner_value.upper() in ['CURRENT_TIMESTAMP', 'NOW', 'CURDATE', 'CURTIME']:
                return inner_value.upper() if column_type.upper() == 'TIMESTAMP' else None
            return f"'{inner_value}'"

        # Default case - add quotes if not already quoted
        if not (default_value.startswith("'") or default_value.startswith('"')):
            # Check if it's a function name
            if default_value.upper() in ['CURRENT_TIMESTAMP', 'NOW', 'CURDATE', 'CURTIME']:
                return default_value.upper() if column_type.upper() == 'TIMESTAMP' else None
            return f"'{default_value}'"

        return default_value

    def create_mysql_table_statement(self, table_name: str, table_info: Dict[str, Any]) -> str:
        """Create MySQL CREATE TABLE statement from SQLite schema"""
        columns = []
        primary_keys = []
        foreign_keys = []

        # Process columns
        for col_info in table_info['columns']:
            cid, name, type_name, notnull, default_value, pk = col_info

            # Convert type
            mysql_type = self.convert_sqlite_type_to_mysql(type_name)

            # Special handling for TEXT columns used as primary keys
            if pk and mysql_type == 'TEXT':
                # Convert TEXT to VARCHAR for primary keys
                mysql_type = 'VARCHAR(255)'

            # Build column definition
            col_def = f"`{name}` {mysql_type}"

            # Collect primary keys
            if pk:
                primary_keys.append(name)

            if notnull and not pk:
                col_def += " NOT NULL"

            # Handle default values
            if default_value is not None:
                mysql_default = self.convert_sqlite_default_to_mysql(str(default_value), mysql_type)
                if mysql_default:
                    col_def += f" DEFAULT {mysql_default}"

            columns.append(col_def)

        # Add AUTO_INCREMENT only for single-column integer primary keys
        if len(primary_keys) == 1:
            pk_column = primary_keys[0]
            # Find the column definition and add AUTO_INCREMENT if it's an integer type
            for i, col_info in enumerate(table_info['columns']):
                cid, name, type_name, notnull, default_value, pk = col_info
                if name == pk_column and pk:
                    mysql_type = self.convert_sqlite_type_to_mysql(type_name)
                    # Special handling for TEXT columns used as primary keys
                    if pk and mysql_type == 'TEXT':
                        mysql_type = 'VARCHAR(255)'

                    if mysql_type in ['INT', 'BIGINT']:
                        # Update the column definition to include AUTO_INCREMENT
                        col_def = f"`{name}` {mysql_type} AUTO_INCREMENT"
                        if notnull and not pk:
                            col_def += " NOT NULL"
                        if default_value is not None:
                            mysql_default = self.convert_sqlite_default_to_mysql(str(default_value), mysql_type)
                            if mysql_default:
                                col_def += f" DEFAULT {mysql_default}"
                        columns[i] = col_def
                    break

        # Add primary key constraint
        if primary_keys:
            columns.append(f"PRIMARY KEY ({', '.join([f'`{pk}`' for pk in primary_keys])})")

        # Process foreign keys
        for fk_info in table_info['foreign_keys']:
            if len(fk_info) >= 5:
                id, seq, ref_table, from_col, to_col = fk_info[:5]
                on_update = fk_info[5] if len(fk_info) > 5 else 'NO ACTION'
                on_delete = fk_info[6] if len(fk_info) > 6 else 'NO ACTION'

                fk_def = f"FOREIGN KEY (`{from_col}`) REFERENCES `{ref_table}`(`{to_col}`)"
                if on_update != 'NO ACTION':
                    fk_def += f" ON UPDATE {on_update}"
                if on_delete != 'NO ACTION':
                    fk_def += f" ON DELETE {on_delete}"

                foreign_keys.append(fk_def)

        # Combine all definitions
        all_definitions = columns + foreign_keys

        # Generate CREATE TABLE statement
        create_sql = f"CREATE TABLE IF NOT EXISTS `{table_name}` (\n"
        create_sql += ",\n".join(f"    {definition}" for definition in all_definitions)
        create_sql += "\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"

        return create_sql

    def create_indexes(self, indexes: List[Tuple]) -> List[str]:
        """Convert SQLite indexes to MySQL"""
        mysql_indexes = []

        for index_info in indexes:
            index_name, table_name, create_sql = index_info

            if create_sql and 'UNIQUE' in create_sql.upper():
                # Extract columns from the SQL
                # This is a simplified parser, might need enhancement for complex cases
                start = create_sql.find('(')
                end = create_sql.rfind(')')
                if start != -1 and end != -1:
                    columns = create_sql[start+1:end].strip()
                    mysql_sql = f"CREATE UNIQUE INDEX `{index_name}` ON `{table_name}` ({columns})"
                    mysql_indexes.append(mysql_sql)
            else:
                # Regular index
                start = create_sql.find('(')
                end = create_sql.rfind(')')
                if start != -1 and end != -1:
                    columns = create_sql[start+1:end].strip()
                    mysql_sql = f"CREATE INDEX `{index_name}` ON `{table_name}` ({columns})"
                    mysql_indexes.append(mysql_sql)

        return mysql_indexes

    def get_table_creation_order(self, schema: Dict[str, Any]) -> List[str]:
        """Get tables in proper creation order based on foreign key dependencies"""

        # Define known dependency order for common tables
        known_order = [
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
            'workout_templates',

            # Tables with multiple foreign keys
            'Recipe_Ingredients',
            'Consumption',
            'recipe_consumption',
            'workout_sets',
            'Sets',
            'Workout',
            'workout_template_exercises',
            'progression_history',

            # Monitoring and tracking tables
            'body_weight_tracking',
            'calorie_tracking',
            'workout_volume_tracking',
            'workout_highlights',
            'set_pattern_ratios',
            'set_progression_history',
            'exercise_progression_patterns',
            'exercise_progression_rules',
            'user_gym_preferences',
            'metric_aggregates',

            # Security and audit tables
            'user_permissions',
            'user_sessions',
            'failed_login_attempts',
            'audit_trail',
            'data_access_log',
            'performance_metrics',
            'metrics',
            'alerts',
            'health_checks',
        ]

        # Get all tables from schema
        all_tables = list(schema['tables'].keys())

        # Start with known order, filtering to existing tables
        ordered_tables = [t for t in known_order if t in all_tables]

        # Add any remaining tables not in known order
        remaining_tables = [t for t in all_tables if t not in ordered_tables]
        ordered_tables.extend(remaining_tables)

        return ordered_tables

    def migrate_schema(self, drop_existing: bool = False) -> bool:
        """Execute complete schema migration"""
        try:
            logger.info("Starting schema migration from SQLite to MySQL")

            # Extract SQLite schema
            schema = self.extract_sqlite_schema()
            logger.info(f"Extracted schema for {len(schema['tables'])} tables")

            # Get table creation order
            table_order = self.get_table_creation_order(schema)
            logger.info(f"Table creation order: {', '.join(table_order[:10])}{'...' if len(table_order) > 10 else ''}")

            # Execute MySQL schema creation
            with self.mysql_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Optionally drop existing tables
                if drop_existing:
                    logger.warning("Dropping existing tables...")
                    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
                    for table_name in reversed(table_order):  # Drop in reverse order
                        if table_name in schema['tables']:
                            cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`")
                    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
                    conn.commit()

                # Disable foreign key checks during creation
                cursor.execute("SET FOREIGN_KEY_CHECKS = 0")

                # Create tables in dependency order
                logger.info("Creating tables...")
                for table_name in table_order:
                    if table_name in schema['tables']:
                        table_info = schema['tables'][table_name]
                        create_sql = self.create_mysql_table_statement(table_name, table_info)
                        try:
                            cursor.execute(create_sql)
                            logger.info(f"Created table: {table_name}")
                        except mysql.connector.Error as e:
                            logger.error(f"Failed to create table {table_name}: {e}")
                            logger.error(f"SQL: {create_sql}")
                            raise

                # Re-enable foreign key checks
                cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

                # Create indexes
                logger.info("Creating indexes...")
                mysql_indexes = self.create_indexes(schema['indexes'])
                for index_sql in mysql_indexes:
                    try:
                        cursor.execute(index_sql)
                        logger.debug(f"Created index: {index_sql[:100]}...")
                    except mysql.connector.Error as e:
                        if "Duplicate key name" in str(e):
                            logger.warning(f"Index already exists: {e}")
                        else:
                            logger.error(f"Failed to create index: {e}")
                            logger.error(f"SQL: {index_sql}")

                conn.commit()

            logger.info("Schema migration completed successfully")
            return True

        except Exception as e:
            logger.error(f"Schema migration failed: {e}")
            return False

    def verify_schema_migration(self) -> Dict[str, Any]:
        """Verify that all tables were created successfully"""
        results = {'success': True, 'tables': {}, 'missing_tables': []}

        try:
            # Get SQLite tables
            with sqlite3.connect(self.sqlite_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
                sqlite_tables = {row[0] for row in cursor.fetchall()}

            # Get MySQL tables
            with self.mysql_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SHOW TABLES")
                mysql_tables = {row[0] for row in cursor.fetchall()}

            # Compare tables
            for table in sqlite_tables:
                if table in mysql_tables:
                    results['tables'][table] = 'Created'
                else:
                    results['missing_tables'].append(table)
                    results['success'] = False

            logger.info(f"Schema verification: {len(results['tables'])} tables created, {len(results['missing_tables'])} missing")

        except Exception as e:
            logger.error(f"Schema verification failed: {e}")
            results['success'] = False
            results['error'] = str(e)

        return results
