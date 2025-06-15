#!/usr/bin/env python3
"""
Sync Development Database to Production (with Backup)
Creates a backup of production database before copying from development
"""

import mysql.connector
import sys
import os
import subprocess
from datetime import datetime

# Database configurations
DEV_CONFIG = {
    'host': '192.168.11.1',
    'port': 3306,
    'user': 'remote_user',
    'password': 'BuGr@d@N4@loB6!',
    'database': 'nutri_tracker_dev',
    'auth_plugin': 'mysql_native_password'
}

PROD_CONFIG = {
    'host': '192.168.11.1',
    'port': 3306,
    'user': 'remote_user',
    'password': 'BuGr@d@N4@loB6!',
    'database': 'nutri_tracker_prod',
    'auth_plugin': 'mysql_native_password'
}

def create_backup():
    """Create a backup of the production database"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"nutri_tracker_prod_backup_{timestamp}.sql"

    print(f"Creating backup of production database: {backup_file}")

    # Use mysqldump to create backup
    cmd = [
        'mysqldump',
        f'--host={PROD_CONFIG["host"]}',
        f'--port={PROD_CONFIG["port"]}',
        f'--user={PROD_CONFIG["user"]}',
        f'--password={PROD_CONFIG["password"]}',
        '--single-transaction',
        '--add-drop-table',
        '--no-tablespaces',
        '--skip-lock-tables',
        PROD_CONFIG['database']
    ]

    try:
        with open(backup_file, 'w') as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)

        if result.returncode == 0:
            # Check if backup file has content
            if os.path.getsize(backup_file) > 1000:  # At least 1KB
                print(f"✓ Backup created successfully: {backup_file}")
                return backup_file
            else:
                print(f"✗ Backup file is too small, may be empty")
                return None
        else:
            print(f"✗ Backup failed: {result.stderr}")
            return None

    except Exception as e:
        print(f"✗ Error creating backup: {e}")
        return None

def restore_backup(backup_file):
    """Restore production database from backup"""
    print(f"Restoring production database from: {backup_file}")

    cmd = [
        'mysql',
        f'--host={PROD_CONFIG["host"]}',
        f'--port={PROD_CONFIG["port"]}',
        f'--user={PROD_CONFIG["user"]}',
        f'--password={PROD_CONFIG["password"]}',
        PROD_CONFIG['database']
    ]

    try:
        with open(backup_file, 'r') as f:
            result = subprocess.run(cmd, stdin=f, stderr=subprocess.PIPE, text=True)

        if result.returncode == 0:
            print("✓ Database restored successfully")
            return True
        else:
            print(f"✗ Restore failed: {result.stderr}")
            return False

    except Exception as e:
        print(f"✗ Error restoring backup: {e}")
        return False

def get_table_list(cursor):
    """Get list of all tables in the database"""
    cursor.execute("SHOW TABLES")
    tables = [table[0] for table in cursor.fetchall()]
    return tables

def get_table_schema(cursor, table_name):
    """Get CREATE TABLE statement for a table"""
    cursor.execute(f"SHOW CREATE TABLE `{table_name}`")
    result = cursor.fetchone()
    return result[1] if result else None

def disable_foreign_key_checks(cursor):
    """Disable foreign key checks"""
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")

def enable_foreign_key_checks(cursor):
    """Enable foreign key checks"""
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

def drop_all_tables(cursor, tables):
    """Drop all tables in reverse order to handle dependencies"""
    print("Dropping all existing tables in production...")
    disable_foreign_key_checks(cursor)

    for table in reversed(tables):
        try:
            cursor.execute(f"DROP TABLE IF EXISTS `{table}`")
            print(f"  ✓ Dropped table: {table}")
        except Exception as e:
            print(f"  ⚠ Warning dropping {table}: {e}")

    enable_foreign_key_checks(cursor)

def create_table_structure(dev_cursor, prod_cursor, table_name):
    """Create table structure in production"""
    schema = get_table_schema(dev_cursor, table_name)
    if schema:
        # Remove AUTO_INCREMENT value from schema to avoid conflicts
        schema_lines = schema.split('\n')
        cleaned_lines = []
        for line in schema_lines:
            if 'AUTO_INCREMENT=' in line:
                # Remove the AUTO_INCREMENT=value part
                line = line.split('AUTO_INCREMENT=')[0].rstrip()
            cleaned_lines.append(line)
        cleaned_schema = '\n'.join(cleaned_lines)

        prod_cursor.execute(cleaned_schema)
        print(f"  ✓ Created table: {table_name}")
        return True
    return False

def copy_table_data(dev_cursor, prod_cursor, table_name):
    """Copy data from dev table to prod table"""
    # Get column names
    dev_cursor.execute(f"DESCRIBE `{table_name}`")
    columns = [col[0] for col in dev_cursor.fetchall()]

    # Get data count
    dev_cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
    count = dev_cursor.fetchone()[0]

    if count == 0:
        print(f"  ✓ {table_name}: No data to copy")
        return True

    # Get all data
    dev_cursor.execute(f"SELECT * FROM `{table_name}`")
    rows = dev_cursor.fetchall()

    if rows:
        # Prepare insert statement
        placeholders = ', '.join(['%s'] * len(columns))
        columns_str = ', '.join([f"`{col}`" for col in columns])
        insert_sql = f"INSERT INTO `{table_name}` ({columns_str}) VALUES ({placeholders})"

        # Insert data in batches
        batch_size = 1000
        inserted = 0

        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            try:
                prod_cursor.executemany(insert_sql, batch)
                inserted += len(batch)
            except Exception as e:
                print(f"  ⚠ Error inserting batch for {table_name}: {e}")
                # Try inserting one by one
                for row in batch:
                    try:
                        prod_cursor.execute(insert_sql, row)
                        inserted += 1
                    except Exception as row_error:
                        print(f"    ⚠ Failed to insert row in {table_name}: {row_error}")

        print(f"  ✓ {table_name}: Copied {inserted}/{count} rows")
        return inserted == count

    return True

def get_table_dependencies():
    """Define table creation order based on dependencies"""
    return [
        # Core tables with no dependencies
        'users',
        'Unit',
        'Ingredient',
        'exercises',
        'MuscleGroup',

        # Tables with simple dependencies
        'Nutrition',
        'Ingredient_Quantity',
        'Recipe',
        'workout_templates',
        'user_gym_preferences',

        # Tables with multiple dependencies
        'Recipe_Ingredients',
        'workout_template_exercises',
        'workout_sessions',
        'Favorites',
        'Consumption',
        'recipe_consumption',
        'calorie_tracking',
        'body_weight_tracking',

        # Workout related tables (depend on sessions)
        'workout_sets',
        'workout_volume_tracking',
        'progression_history',
        'set_progression_history',
        'exercise_progression_rules',
        'exercise_progression_patterns',
        'set_pattern_ratios',
        'workout_highlights',

        # Legacy tables
        'Workout',
        'Exercise',
        'Sets'
    ]

def sync_database_with_backup():
    """Main function to sync dev database to production with backup"""
    print("="*60)
    print("SYNCING DEVELOPMENT TO PRODUCTION DATABASE (WITH BACKUP)")
    print("="*60)
    print(f"Source: {DEV_CONFIG['database']} at {DEV_CONFIG['host']}")
    print(f"Target: {PROD_CONFIG['database']} at {PROD_CONFIG['host']}")
    print("="*60)

    # Step 1: Create backup
    backup_file = create_backup()
    if not backup_file:
        print("✗ Failed to create backup. Aborting sync.")
        return False

    # Connect to both databases
    try:
        print("\nConnecting to development database...")
        dev_conn = mysql.connector.connect(**DEV_CONFIG)
        dev_cursor = dev_conn.cursor()
        print("✓ Connected to development database")

        print("Connecting to production database...")
        prod_conn = mysql.connector.connect(**PROD_CONFIG)
        prod_cursor = prod_conn.cursor()
        print("✓ Connected to production database")

    except Exception as e:
        print(f"✗ Connection error: {e}")
        return False

    try:
        # Get list of tables from development
        dev_tables = get_table_list(dev_cursor)
        print(f"\nFound {len(dev_tables)} tables in development database")

        # Get list of tables from production (for cleanup)
        prod_tables = get_table_list(prod_cursor)
        print(f"Found {len(prod_tables)} tables in production database")

        # Confirm operation
        print(f"\n⚠ This will replace ALL DATA in production database.")
        print(f"Backup created: {backup_file}")
        if input("Continue with sync? (yes/no): ").lower() != 'yes':
            print("Operation cancelled.")
            return False

        # Step 2: Drop all existing tables in production
        if prod_tables:
            drop_all_tables(prod_cursor, prod_tables)
            prod_conn.commit()

        # Step 3: Create table structure
        print("\nCreating table structures...")
        disable_foreign_key_checks(prod_cursor)

        # Get ordered table list
        ordered_tables = get_table_dependencies()

        # Add any tables not in our predefined list
        remaining_tables = [t for t in dev_tables if t not in ordered_tables]
        all_tables = ordered_tables + remaining_tables

        # Filter to only tables that exist in dev
        tables_to_create = [t for t in all_tables if t in dev_tables]

        created_tables = []
        for table in tables_to_create:
            if create_table_structure(dev_cursor, prod_cursor, table):
                created_tables.append(table)

        prod_conn.commit()
        print(f"Created {len(created_tables)} tables")

        # Step 4: Copy data
        print("\nCopying data...")
        total_success = 0
        total_tables = len(created_tables)

        for table in created_tables:
            if copy_table_data(dev_cursor, prod_cursor, table):
                total_success += 1
            prod_conn.commit()  # Commit after each table

        enable_foreign_key_checks(prod_cursor)
        prod_conn.commit()

        print("\n" + "="*60)
        print("SYNC SUMMARY")
        print("="*60)
        print(f"Tables processed: {total_success}/{total_tables}")
        print(f"Success rate: {(total_success/total_tables)*100:.1f}%")
        print(f"Backup file: {backup_file}")

        if total_success == total_tables:
            print("✅ Database sync completed successfully!")
            print(f"💾 Backup saved as: {backup_file}")
        else:
            print("⚠ Database sync completed with some issues")
            print("Consider restoring from backup if needed")

        return total_success == total_tables

    except Exception as e:
        print(f"\n✗ Error during sync: {e}")
        print("Attempting to restore from backup...")

        prod_conn.rollback()
        prod_conn.close()

        # Attempt to restore backup
        if restore_backup(backup_file):
            print("✓ Production database restored from backup")
        else:
            print("✗ Failed to restore backup - manual intervention required")

        return False

    finally:
        if 'dev_conn' in locals():
            dev_conn.close()
        if 'prod_conn' in locals():
            prod_conn.close()

if __name__ == "__main__":
    print("Development to Production Database Sync (with Backup)")
    print("This script will:")
    print("1. Create a backup of the production database")
    print("2. Replace production database with development data")
    print("3. Restore from backup if anything goes wrong")
    print()

    success = sync_database_with_backup()
    sys.exit(0 if success else 1)
