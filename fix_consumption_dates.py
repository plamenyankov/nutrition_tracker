#!/usr/bin/env python3
"""
Fix consumption date format issues and migrate remaining records
"""

import sqlite3
import mysql.connector
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def convert_date_format(date_str):
    """Convert DD.MM.YYYY to YYYY-MM-DD"""
    try:
        # Parse DD.MM.YYYY format
        date_obj = datetime.strptime(date_str, '%d.%m.%Y')
        # Return YYYY-MM-DD format
        return date_obj.strftime('%Y-%m-%d')
    except ValueError:
        try:
            # Try DD.MM.YY format
            date_obj = datetime.strptime(date_str, '%d.%m.%y')
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            print(f"Warning: Could not parse date: {date_str}")
            return None

def fix_consumption_data():
    """Fix consumption data with date format conversion"""

    # Database connections
    sqlite_path = 'database_old.db'
    mysql_config = {
        'host': os.getenv('DB_HOST', '192.168.11.1'),
        'port': int(os.getenv('DB_PORT', '3306')),
        'database': os.getenv('DB_NAME_DEV', 'nutri_tracker_dev'),
        'user': os.getenv('DB_USER', 'remote_user'),
        'password': os.getenv('DB_PASS', 'BuGr@d@N4@loB6!'),
        'auth_plugin': 'mysql_native_password'
    }

    print("=== FIXING CONSUMPTION DATA ===")

    # Get all consumption data from SQLite
    with sqlite3.connect(sqlite_path) as sqlite_conn:
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT * FROM Consumption")
        consumption_data = cursor.fetchall()

        # Get column names
        cursor.execute("PRAGMA table_info(Consumption)")
        columns = [row[1] for row in cursor.fetchall()]

    print(f"Found {len(consumption_data)} consumption records in SQLite")

    # Connect to MySQL and fix the data
    mysql_conn = mysql.connector.connect(**mysql_config)
    mysql_cursor = mysql_conn.cursor()

    # Clear existing consumption data to avoid conflicts
    mysql_cursor.execute("DELETE FROM Consumption")
    mysql_conn.commit()
    print("Cleared existing consumption data from MySQL")

    # Insert data with date conversion
    successful_inserts = 0
    failed_inserts = 0

    for row in consumption_data:
        try:
            # Convert row to dict for easier handling
            row_dict = dict(zip(columns, row))

            # Convert date format
            if 'consumption_date' in row_dict:
                original_date = row_dict['consumption_date']
                converted_date = convert_date_format(original_date)

                if converted_date:
                    row_dict['consumption_date'] = converted_date

                    # Insert into MySQL
                    placeholders = ', '.join(['%s'] * len(columns))
                    column_names = ', '.join([f'`{col}`' for col in columns])

                    insert_query = f"INSERT INTO Consumption ({column_names}) VALUES ({placeholders})"
                    values = [row_dict[col] for col in columns]

                    mysql_cursor.execute(insert_query, values)
                    successful_inserts += 1
                else:
                    print(f"Skipping record with invalid date: {original_date}")
                    failed_inserts += 1
            else:
                print("No consumption_date column found")
                failed_inserts += 1

        except Exception as e:
            print(f"Error inserting record: {e}")
            failed_inserts += 1

    mysql_conn.commit()
    mysql_cursor.close()
    mysql_conn.close()

    print(f"\n=== RESULTS ===")
    print(f"✓ Successfully inserted: {successful_inserts} records")
    print(f"✗ Failed to insert: {failed_inserts} records")
    print(f"Total processed: {len(consumption_data)} records")

    return successful_inserts, failed_inserts

def fix_weight_data():
    """Fix body weight tracking data with date format conversion"""

    # Database connections
    sqlite_path = 'database_old.db'
    mysql_config = {
        'host': os.getenv('DB_HOST', '192.168.11.1'),
        'port': int(os.getenv('DB_PORT', '3306')),
        'database': os.getenv('DB_NAME_DEV', 'nutri_tracker_dev'),
        'user': os.getenv('DB_USER', 'remote_user'),
        'password': os.getenv('DB_PASS', 'BuGr@d@N4@loB6!'),
        'auth_plugin': 'mysql_native_password'
    }

    print("\n=== FIXING WEIGHT DATA ===")

    # Get all weight data from SQLite
    with sqlite3.connect(sqlite_path) as sqlite_conn:
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT * FROM body_weight_tracking")
        weight_data = cursor.fetchall()

        # Get column names
        cursor.execute("PRAGMA table_info(body_weight_tracking)")
        columns = [row[1] for row in cursor.fetchall()]

    print(f"Found {len(weight_data)} weight records in SQLite")

    # Connect to MySQL and fix the data
    mysql_conn = mysql.connector.connect(**mysql_config)
    mysql_cursor = mysql_conn.cursor()

    # Clear existing weight data to avoid conflicts
    mysql_cursor.execute("DELETE FROM body_weight_tracking")
    mysql_conn.commit()
    print("Cleared existing weight data from MySQL")

    # Insert data with date conversion
    successful_inserts = 0
    failed_inserts = 0

    for row in weight_data:
        try:
            # Convert row to dict for easier handling
            row_dict = dict(zip(columns, row))

            # Convert date format
            if 'date' in row_dict:
                original_date = row_dict['date']
                converted_date = convert_date_format(original_date)

                if converted_date:
                    row_dict['date'] = converted_date

                    # Insert into MySQL
                    placeholders = ', '.join(['%s'] * len(columns))
                    column_names = ', '.join([f'`{col}`' for col in columns])

                    insert_query = f"INSERT INTO body_weight_tracking ({column_names}) VALUES ({placeholders})"
                    values = [row_dict[col] for col in columns]

                    mysql_cursor.execute(insert_query, values)
                    successful_inserts += 1
                else:
                    print(f"Skipping record with invalid date: {original_date}")
                    failed_inserts += 1
            else:
                print("No date column found")
                failed_inserts += 1

        except Exception as e:
            print(f"Error inserting record: {e}")
            failed_inserts += 1

    mysql_conn.commit()
    mysql_cursor.close()
    mysql_conn.close()

    print(f"\n=== WEIGHT RESULTS ===")
    print(f"✓ Successfully inserted: {successful_inserts} records")
    print(f"✗ Failed to insert: {failed_inserts} records")
    print(f"Total processed: {len(weight_data)} records")

    return successful_inserts, failed_inserts

if __name__ == "__main__":
    print("Starting consumption and weight data fix...")

    # Fix consumption data
    consumption_success, consumption_failed = fix_consumption_data()

    # Fix weight data
    weight_success, weight_failed = fix_weight_data()

    print(f"\n=== FINAL SUMMARY ===")
    print(f"Consumption: {consumption_success} success, {consumption_failed} failed")
    print(f"Weight: {weight_success} success, {weight_failed} failed")
    print("Data fix completed!")
