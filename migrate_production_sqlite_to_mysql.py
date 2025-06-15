#!/usr/bin/env python3
"""
Migrate production SQLite database.db to production MySQL
This script should be run on the production server
"""

import os
import sys
import sqlite3
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.database.connection_manager import get_db_manager

def migrate_production_data():
    """Migrate production SQLite to production MySQL"""
    print("="*60)
    print("MIGRATING PRODUCTION SQLITE TO PRODUCTION MYSQL")
    print("="*60)

    # Check if we're on production server
    sqlite_path = 'database.db'
    if not os.path.exists(sqlite_path):
        print(f"Error: {sqlite_path} not found. This script should be run on the production server.")
        return False

    # Connect to production SQLite
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_cursor = sqlite_conn.cursor()

    # Connect to production MySQL
    os.environ['FLASK_ENV'] = 'production'
    mysql_db = get_db_manager(use_mysql=True)

    try:
        print("Checking SQLite data...")

        # Check what data we have in SQLite
        tables_to_check = [
            'users', 'exercises', 'Unit', 'workout_sessions', 'workout_sets',
            'workout_templates', 'workout_template_exercises', 'Consumption',
            'Ingredient', 'Recipe', 'body_weight_tracking', 'calorie_tracking'
        ]

        sqlite_data = {}
        for table in tables_to_check:
            try:
                sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = sqlite_cursor.fetchone()[0]
                sqlite_data[table] = count
                print(f"  SQLite {table}: {count} rows")
            except Exception as e:
                print(f"  SQLite {table}: Error - {e}")
                sqlite_data[table] = 0

        print("\nChecking MySQL data...")
        with mysql_db.get_connection() as mysql_conn:
            mysql_cursor = mysql_conn.cursor()

            mysql_data = {}
            for table in tables_to_check:
                try:
                    mysql_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = mysql_cursor.fetchone()[0]
                    mysql_data[table] = count
                    print(f"  MySQL {table}: {count} rows")
                except Exception as e:
                    print(f"  MySQL {table}: Error - {e}")
                    mysql_data[table] = 0

        print("\nMigrating data...")

        with mysql_db.get_connection() as mysql_conn:
            mysql_cursor = mysql_conn.cursor()

            # Migrate essential tables that are missing or have less data in MySQL
            migration_plan = []

            for table in tables_to_check:
                sqlite_count = sqlite_data.get(table, 0)
                mysql_count = mysql_data.get(table, 0)

                if sqlite_count > 0 and (mysql_count == 0 or sqlite_count > mysql_count):
                    migration_plan.append((table, sqlite_count))
                    print(f"  Will migrate {table}: {sqlite_count} rows")

            if not migration_plan:
                print("No data to migrate - MySQL already has all the data")
                return True

            # Execute migrations
            for table, count in migration_plan:
                print(f"\nMigrating {table}...")

                try:
                    # Get all data from SQLite
                    sqlite_cursor.execute(f"SELECT * FROM {table}")
                    rows = sqlite_cursor.fetchall()

                    if not rows:
                        print(f"  No data in SQLite {table}")
                        continue

                    # Get column info
                    sqlite_cursor.execute(f"PRAGMA table_info({table})")
                    columns = sqlite_cursor.fetchall()
                    col_names = [col[1] for col in columns]

                    # Handle special cases for tables with timing columns
                    if table in ['workout_sessions', 'workout_sets']:
                        # Filter out timing columns that don't exist in MySQL yet
                        timing_columns = ['started_at', 'completed_at', 'duration_seconds', 'rest_duration_seconds']
                        filtered_columns = [col for col in col_names if col not in timing_columns]

                        # Get filtered data
                        col_indices = [col_names.index(col) for col in filtered_columns]
                        filtered_rows = []
                        for row in rows:
                            filtered_row = tuple(row[i] for i in col_indices)
                            filtered_rows.append(filtered_row)

                        col_names = filtered_columns
                        rows = filtered_rows

                    # Clear existing data in MySQL
                    mysql_cursor.execute(f"DELETE FROM {table}")

                    # Insert data
                    placeholders = ', '.join(['%s'] * len(col_names))
                    columns_str = ', '.join(col_names)

                    mysql_cursor.executemany(
                        f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})",
                        rows
                    )

                    print(f"  ✓ Migrated {len(rows)} rows to {table}")

                except Exception as e:
                    print(f"  ✗ Error migrating {table}: {e}")
                    # Continue with other tables

            mysql_conn.commit()

        print("\n" + "="*60)
        print("✓ PRODUCTION MIGRATION COMPLETED!")
        print("="*60)

        # Final verification
        print("\nFinal verification:")
        with mysql_db.get_connection() as mysql_conn:
            mysql_cursor = mysql_conn.cursor()

            for table in ['users', 'exercises', 'workout_sessions', 'workout_sets']:
                mysql_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = mysql_cursor.fetchone()[0]
                print(f"  MySQL {table}: {count} rows")

        return True

    except Exception as e:
        print(f"Error during migration: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        sqlite_conn.close()

if __name__ == "__main__":
    success = migrate_production_data()
    if success:
        print("\n🎉 Production data migration completed successfully!")
        print("You can now test the timer functionality with real data.")
    else:
        print("\n❌ Migration failed. Please check the errors above.")

    sys.exit(0 if success else 1)
