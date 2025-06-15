#!/usr/bin/env python3
"""
Simple migration script for production server
Migrates SQLite database to MySQL with minimal dependencies
"""

import sqlite3
import mysql.connector
import sys
import os
from datetime import datetime

# Development MySQL credentials (using local VPN)
MYSQL_CONFIG = {
    'host': '192.168.11.1',
    'port': 3306,
    'user': 'remote_user',
    'password': 'BuGr@d@N4@loB6!',
    'database': 'nutri_tracker_dev',
    'auth_plugin': 'mysql_native_password'
}

def convert_date_format(date_str):
    """Convert DD.MM.YYYY to YYYY-MM-DD"""
    if not date_str or date_str == 'NULL':
        return None

    try:
        # Try DD.MM.YYYY format first
        if '.' in date_str:
            day, month, year = date_str.split('.')
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        # If already in YYYY-MM-DD format, return as is
        elif '-' in date_str and len(date_str) == 10:
            return date_str
        else:
            return date_str
    except:
        return None

def migrate_data(source_db):
    """Migrate data from SQLite to MySQL"""
    print("="*60)
    print("SIMPLE PRODUCTION MIGRATION")
    print("="*60)

    # Connect to SQLite
    if not os.path.exists(source_db):
        print(f"✗ Source database not found: {source_db}")
        return False

    sqlite_conn = sqlite3.connect(source_db)
    sqlite_cursor = sqlite_conn.cursor()
    print(f"✓ Connected to SQLite: {source_db}")

    # Connect to MySQL
    try:
        mysql_conn = mysql.connector.connect(**MYSQL_CONFIG)
        mysql_cursor = mysql_conn.cursor()
        print(f"✓ Connected to MySQL at {MYSQL_CONFIG['host']}")
    except Exception as e:
        print(f"✗ Failed to connect to MySQL: {e}")
        return False

    # Tables to migrate with special handling
    tables_config = {
        'users': {'clear': False},  # Don't clear users
        'exercises': {'clear': False},  # Don't clear exercises
        'Unit': {'clear': False},  # Don't clear units
        'Ingredient': {'clear': False},  # Don't clear ingredients
        'Recipe': {'clear': False},  # Don't clear recipes
        'workout_templates': {'clear': False},  # Don't clear templates
        'workout_template_exercises': {'clear': False},  # Don't clear template exercises
        'workout_sessions': {'clear': True, 'date_columns': ['date']},
        'workout_sets': {'clear': True},
        'Consumption': {'clear': True, 'date_columns': ['consumption_date']},
        'body_weight_tracking': {'clear': True, 'date_columns': ['date']},
        'calorie_tracking': {'clear': True, 'date_columns': ['date']},
        'workout_volume_tracking': {'clear': True, 'date_columns': ['date']},
    }

    success_count = 0

    for table, config in tables_config.items():
        try:
            # Check if table exists in SQLite
            sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            if not sqlite_cursor.fetchone():
                print(f"  {table}: Table not found in source database")
                continue

            # Get data from SQLite
            sqlite_cursor.execute(f"SELECT * FROM {table}")
            rows = sqlite_cursor.fetchall()

            if not rows:
                print(f"  {table}: No data to migrate")
                continue

            # Get column names
            sqlite_cursor.execute(f"PRAGMA table_info({table})")
            columns = sqlite_cursor.fetchall()
            col_names = [col[1] for col in columns]

            # Get MySQL columns to filter
            mysql_cursor.execute(f"DESCRIBE {table}")
            mysql_columns = [col[0] for col in mysql_cursor.fetchall()]

            # Filter columns that exist in MySQL
            filtered_columns = [col for col in col_names if col in mysql_columns]
            col_indices = [col_names.index(col) for col in filtered_columns]

            # Process rows
            processed_rows = []
            date_columns = config.get('date_columns', [])

            for row in rows:
                # Filter columns
                filtered_row = list(row[i] for i in col_indices)

                # Convert date formats
                for i, col_name in enumerate(filtered_columns):
                    if col_name in date_columns and filtered_row[i]:
                        converted_date = convert_date_format(str(filtered_row[i]))
                        if converted_date:
                            filtered_row[i] = converted_date
                        else:
                            # Skip rows with invalid dates
                            filtered_row = None
                            break

                if filtered_row:
                    processed_rows.append(tuple(filtered_row))

            if not processed_rows:
                print(f"  {table}: No valid data after processing")
                continue

            # Clear existing data if configured
            if config.get('clear', False):
                mysql_cursor.execute(f"DELETE FROM {table}")
                print(f"  {table}: Cleared existing data")

            # Insert data
            placeholders = ', '.join(['%s'] * len(filtered_columns))
            columns_str = ', '.join(filtered_columns)

            # Insert one by one to handle duplicates
            inserted_count = 0
            for row in processed_rows:
                try:
                    mysql_cursor.execute(
                        f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})",
                        row
                    )
                    inserted_count += 1
                except mysql.connector.IntegrityError:
                    # Skip duplicates
                    pass
                except Exception as e:
                    print(f"    Warning: Failed to insert row: {e}")

            mysql_conn.commit()
            print(f"  ✓ {table}: Migrated {inserted_count}/{len(processed_rows)} rows")
            success_count += 1

        except Exception as e:
            print(f"  ✗ {table}: Error - {e}")
            mysql_conn.rollback()

    # Close connections
    sqlite_conn.close()
    mysql_conn.close()

    print("\n" + "="*60)
    print(f"✓ Migration completed: {success_count}/{len(tables_config)} tables")
    print("="*60)

    return success_count > 0

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python simple_migrate_prod.py <source_database.db>")
        sys.exit(1)

    source_database = sys.argv[1]
    success = migrate_data(source_database)
    sys.exit(0 if success else 1)
