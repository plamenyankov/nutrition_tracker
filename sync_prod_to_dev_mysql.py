#!/usr/bin/env python3
"""
Sync production MySQL schema to development MySQL database
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.database.connection_manager import get_db_manager

def sync_mysql_to_mysql():
    """Sync production MySQL schema and data to development MySQL"""
    print("="*60)
    print("SYNCING PRODUCTION MYSQL TO DEVELOPMENT MYSQL")
    print("="*60)

    try:
        # Get production schema and data
        print("Getting production schema and data...")
        os.environ['FLASK_ENV'] = 'production'
        prod_db = get_db_manager(use_mysql=True)

        with prod_db.get_connection() as prod_conn:
            prod_cursor = prod_conn.cursor()

            # Get all tables
            prod_cursor.execute("SHOW TABLES")
            tables = [table[0] for table in prod_cursor.fetchall()]
            print(f"Found {len(tables)} tables in production")

            # Get CREATE TABLE statements for each table
            table_schemas = {}
            table_data = {}

            for table in tables:
                prod_cursor.execute(f"SHOW CREATE TABLE {table}")
                create_sql = prod_cursor.fetchone()[1]
                table_schemas[table] = create_sql

                # Get data
                prod_cursor.execute(f"SELECT * FROM {table}")
                rows = prod_cursor.fetchall()
                table_data[table] = rows
                print(f"  - {table}: {len(rows)} rows")

        # Apply schema to development
        print("\nApplying schema to development database...")
        os.environ['FLASK_ENV'] = 'development'
        dev_db = get_db_manager(use_mysql=True)

        with dev_db.get_connection() as dev_conn:
            dev_cursor = dev_conn.cursor()

            # Drop existing tables (in reverse order to handle foreign keys)
            print("Dropping existing tables...")
            dev_cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            for table in reversed(tables):
                try:
                    dev_cursor.execute(f"DROP TABLE IF EXISTS {table}")
                    print(f"  Dropped {table}")
                except Exception as e:
                    print(f"  Warning: Could not drop {table}: {e}")

            # Create tables
            print("Creating tables...")
            for table in tables:
                try:
                    dev_cursor.execute(table_schemas[table])
                    print(f"  ✓ Created {table}")
                except Exception as e:
                    print(f"  ✗ Failed to create {table}: {e}")

            dev_cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
            dev_conn.commit()

        # Sync data
        print("\nSyncing data...")
        essential_tables = ['users', 'exercises', 'Unit', 'workout_sessions', 'workout_sets', 'workout_templates', 'workout_template_exercises']

        with dev_db.get_connection() as dev_conn:
            dev_cursor = dev_conn.cursor()

            for table in essential_tables:
                if table in tables and table_data[table]:
                    print(f"  Syncing {table}...")

                    rows = table_data[table]
                    if rows:
                        # Get column count from production
                        os.environ['FLASK_ENV'] = 'production'
                        with prod_db.get_connection() as prod_conn:
                            prod_cursor = prod_conn.cursor()
                            prod_cursor.execute(f"DESCRIBE {table}")
                            columns = prod_cursor.fetchall()
                            col_count = len(columns)

                        # Reset to development
                        os.environ['FLASK_ENV'] = 'development'

                        # Insert into development
                        placeholders = ', '.join(['%s'] * col_count)
                        dev_cursor.executemany(
                            f"INSERT INTO {table} VALUES ({placeholders})",
                            rows
                        )
                        print(f"    ✓ Synced {len(rows)} rows")
                    else:
                        print(f"    No data in {table}")
                elif table in tables:
                    print(f"  {table}: No data to sync")

            dev_conn.commit()

        print("\n" + "="*60)
        print("✓ MYSQL TO MYSQL SYNC COMPLETED!")
        print("="*60)

        # Verify sync
        os.environ['FLASK_ENV'] = 'development'
        with dev_db.get_connection() as dev_conn:
            dev_cursor = dev_conn.cursor()

            print("\nVerification:")
            for table in essential_tables:
                if table in tables:
                    dev_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = dev_cursor.fetchone()[0]
                    print(f"  {table}: {count} rows")

        return True

    except Exception as e:
        print(f"Error syncing databases: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = sync_mysql_to_mysql()
    sys.exit(0 if success else 1)
