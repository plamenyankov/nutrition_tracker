#!/usr/bin/env python3
"""
Sync production MySQL schema and data to local SQLite development database
This ensures dev/prod parity for proper testing workflow
"""

import os
import sys
import sqlite3
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.database import get_database_config
from models.database.connection_manager import get_db_manager

def get_mysql_schema():
    """Get the complete schema from production MySQL"""
    print("Connecting to production MySQL...")

    # Set environment to production to get MySQL connection
    os.environ['FLASK_ENV'] = 'production'

    db_manager = get_db_manager(use_mysql=True)

    schema_info = {}

    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Get all tables
            cursor.execute("SHOW TABLES")
            tables = [table[0] for table in cursor.fetchall()]

            print(f"Found {len(tables)} tables in production MySQL")

            for table in tables:
                print(f"  Analyzing table: {table}")

                # Get table structure
                cursor.execute(f"DESCRIBE {table}")
                columns = cursor.fetchall()

                # Get table creation SQL (we'll adapt this for SQLite)
                cursor.execute(f"SHOW CREATE TABLE {table}")
                create_sql = cursor.fetchone()[1]

                # Get sample data count
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                row_count = cursor.fetchone()[0]

                schema_info[table] = {
                    'columns': columns,
                    'create_sql': create_sql,
                    'row_count': row_count
                }

    except Exception as e:
        print(f"Error getting MySQL schema: {e}")
        return None

    return schema_info, tables

def convert_mysql_to_sqlite_schema(mysql_schema):
    """Convert MySQL schema to SQLite compatible schema"""
    sqlite_schemas = {}

    # Type mapping from MySQL to SQLite
    type_mapping = {
        'int': 'INTEGER',
        'bigint': 'INTEGER',
        'tinyint': 'INTEGER',
        'smallint': 'INTEGER',
        'mediumint': 'INTEGER',
        'varchar': 'TEXT',
        'char': 'TEXT',
        'text': 'TEXT',
        'longtext': 'TEXT',
        'mediumtext': 'TEXT',
        'tinytext': 'TEXT',
        'float': 'REAL',
        'double': 'REAL',
        'decimal': 'REAL',
        'date': 'DATE',
        'datetime': 'TIMESTAMP',
        'timestamp': 'TIMESTAMP',
        'boolean': 'BOOLEAN',
        'bool': 'BOOLEAN'
    }

    for table_name, table_info in mysql_schema.items():
        columns = table_info['columns']

        # Build SQLite CREATE TABLE statement
        sqlite_columns = []
        primary_key_columns = []

        for col in columns:
            col_name = col[0]
            col_type = col[1].lower()
            is_nullable = col[2] == 'YES'
            col_key = col[3]
            col_default = col[4]
            col_extra = col[5]

            # Convert MySQL type to SQLite type
            sqlite_type = 'TEXT'  # Default
            for mysql_type, sqlite_equiv in type_mapping.items():
                if mysql_type in col_type:
                    sqlite_type = sqlite_equiv
                    break

            # Build column definition
            col_def = f"{col_name} {sqlite_type}"

            # Handle primary key - collect them for composite primary key handling
            if col_key == 'PRI':
                primary_key_columns.append(col_name)
                if 'auto_increment' in col_extra.lower() and len(primary_key_columns) == 1:
                    # Single column auto-increment primary key
                    col_def = f"{col_name} INTEGER PRIMARY KEY AUTOINCREMENT"
                else:
                    # Part of composite primary key or regular primary key
                    pass  # Will handle at the end

            # Handle NOT NULL
            if not is_nullable and col_key != 'PRI':
                col_def += " NOT NULL"

            # Handle defaults (simplified)
            if col_default and col_default != 'NULL':
                if col_default == 'CURRENT_TIMESTAMP':
                    col_def += " DEFAULT CURRENT_TIMESTAMP"
                elif col_default.isdigit():
                    col_def += f" DEFAULT {col_default}"
                else:
                    col_def += f" DEFAULT '{col_default}'"

            sqlite_columns.append(col_def)

        # Handle composite primary keys
        if len(primary_key_columns) > 1:
            # Add composite primary key constraint
            pk_constraint = f"PRIMARY KEY ({', '.join(primary_key_columns)})"
            sqlite_columns.append(pk_constraint)
        elif len(primary_key_columns) == 1 and 'auto_increment' not in str(columns).lower():
            # Single primary key without auto-increment
            for i, col_def in enumerate(sqlite_columns):
                if col_def.startswith(primary_key_columns[0]):
                    sqlite_columns[i] = col_def + " PRIMARY KEY"
                    break

        # Create the SQLite CREATE TABLE statement
        create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} (\n    " + ",\n    ".join(sqlite_columns) + "\n)"

        sqlite_schemas[table_name] = {
            'create_sql': create_sql,
            'row_count': table_info['row_count']
        }

    return sqlite_schemas

def create_local_dev_database(sqlite_schemas, table_order):
    """Create/update local SQLite database with production schema"""
    print("\nCreating local development database...")

    # Backup existing database if it exists
    if os.path.exists('database.db'):
        import shutil
        backup_name = f"database_backup_{int(os.path.getmtime('database.db'))}.db"
        shutil.copy2('database.db', backup_name)
        print(f"Backed up existing database to {backup_name}")

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    try:
        # Create tables in dependency order
        created_tables = []

        for table_name in table_order:
            if table_name in sqlite_schemas:
                print(f"Creating table: {table_name}")
                cursor.execute(sqlite_schemas[table_name]['create_sql'])
                created_tables.append(table_name)

        # Add any missing tables that weren't in the order
        for table_name in sqlite_schemas:
            if table_name not in created_tables:
                print(f"Creating remaining table: {table_name}")
                cursor.execute(sqlite_schemas[table_name]['create_sql'])

        conn.commit()
        print(f"✓ Created {len(sqlite_schemas)} tables in local database")

        return True

    except Exception as e:
        print(f"Error creating local database: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def sync_essential_data():
    """Sync essential data from production to local dev database"""
    print("\nSyncing essential data from production...")

    # Tables to sync data for (essential reference data)
    essential_tables = ['exercises', 'Unit', 'users']

    # Set environment to production for MySQL connection
    os.environ['FLASK_ENV'] = 'production'
    mysql_db = get_db_manager(use_mysql=True)

    # Local SQLite connection
    sqlite_conn = sqlite3.connect('database.db')
    sqlite_cursor = sqlite_conn.cursor()

    try:
        with mysql_db.get_connection() as mysql_conn:
            mysql_cursor = mysql_conn.cursor()

            for table in essential_tables:
                try:
                    print(f"  Syncing {table}...")

                    # Get data from MySQL
                    mysql_cursor.execute(f"SELECT * FROM {table}")
                    rows = mysql_cursor.fetchall()

                    if not rows:
                        print(f"    No data in {table}")
                        continue

                    # Get column count
                    mysql_cursor.execute(f"DESCRIBE {table}")
                    columns = mysql_cursor.fetchall()
                    col_count = len(columns)

                    # Clear existing data
                    sqlite_cursor.execute(f"DELETE FROM {table}")

                    # Insert data
                    placeholders = ', '.join(['?'] * col_count)
                    sqlite_cursor.executemany(
                        f"INSERT INTO {table} VALUES ({placeholders})",
                        rows
                    )

                    print(f"    ✓ Synced {len(rows)} rows")

                except Exception as e:
                    print(f"    Error syncing {table}: {e}")

        sqlite_conn.commit()
        print("✓ Essential data sync completed")

    except Exception as e:
        print(f"Error syncing data: {e}")
        sqlite_conn.rollback()
    finally:
        sqlite_conn.close()

def main():
    """Main sync process"""
    print("="*60)
    print("SYNCING PRODUCTION SCHEMA TO LOCAL DEVELOPMENT")
    print("="*60)

    # Step 1: Get production MySQL schema
    mysql_schema, table_order = get_mysql_schema()
    if not mysql_schema:
        print("Failed to get MySQL schema")
        return False

    # Step 2: Convert to SQLite schema
    print("\nConverting MySQL schema to SQLite...")
    sqlite_schemas = convert_mysql_to_sqlite_schema(mysql_schema)
    print(f"✓ Converted {len(sqlite_schemas)} table schemas")

    # Step 3: Create local database
    if not create_local_dev_database(sqlite_schemas, table_order):
        print("Failed to create local database")
        return False

    # Step 4: Sync essential data
    sync_essential_data()

    print("\n" + "="*60)
    print("✓ DEV/PROD SCHEMA SYNC COMPLETED!")
    print("="*60)
    print("\nLocal development database now matches production schema.")
    print("You can now develop and test locally before deploying to production.")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
