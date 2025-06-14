#!/usr/bin/env python3
"""
Test script to verify the app is using MySQL database
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.database.connection_manager import get_db_manager

def test_app_database_connection():
    """Test what database the app is actually using"""

    print("="*60)
    print("APP DATABASE CONNECTION TEST")
    print("="*60)

    # Check environment variables
    use_mysql = os.getenv('USE_MYSQL', 'false').lower() == 'true'
    db_host = os.getenv('DB_HOST', 'Not set')
    db_name_dev = os.getenv('DB_NAME_DEV', 'Not set')

    print(f"USE_MYSQL environment variable: {use_mysql}")
    print(f"DB_HOST: {db_host}")
    print(f"DB_NAME_DEV: {db_name_dev}")

    # Test database connection
    try:
        db_manager = get_db_manager()

        print(f"\nDatabase Manager Configuration:")
        print(f"Using MySQL: {db_manager.use_mysql}")

        if db_manager.use_mysql:
            print(f"MySQL Host: {db_manager.config.host}")
            print(f"MySQL Port: {db_manager.config.port}")
            print(f"MySQL Database: {db_manager.config.database}")
            print(f"MySQL User: {db_manager.config.username}")
        else:
            print(f"SQLite Path: {db_manager.sqlite_path}")

        # Test connection
        print(f"\nTesting database connection...")
        if db_manager.test_connection():
            print("✓ Database connection successful!")

            # Get table info
            tables = db_manager.get_table_info()
            print(f"\nAvailable tables: {len(tables)}")
            for table_name, info in list(tables.items())[:5]:  # Show first 5 tables
                print(f"  - {table_name}: {info.get('row_count', 'N/A')} rows")
            if len(tables) > 5:
                print(f"  ... and {len(tables) - 5} more tables")

        else:
            print("✗ Database connection failed!")
            return False

    except Exception as e:
        print(f"✗ Error testing database: {e}")
        return False

    print("\n" + "="*60)
    if db_manager.use_mysql:
        print("✓ YOUR APP IS NOW USING MYSQL DATABASE!")
        print(f"✓ Connected to: {db_manager.config.host}:{db_manager.config.port}")
        print(f"✓ Database: {db_manager.config.database}")
    else:
        print("⚠️  Your app is still using SQLite database")
        print("   Check your .env file configuration")
    print("="*60)

    return True

if __name__ == "__main__":
    test_app_database_connection()
