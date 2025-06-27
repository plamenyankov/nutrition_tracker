#!/usr/bin/env python3
"""
Test app database configuration
"""
import os
import sys

def test_app_database_config():
    """Test that the app can initialize its database configuration"""

    print("============================================================")
    print("APP DATABASE CONNECTION TEST")
    print("============================================================")

    # Display environment variables
    print(f"USE_MYSQL environment variable: {os.getenv('USE_MYSQL')}")
    print(f"DB_HOST: {os.getenv('DB_HOST')}")
    print(f"DB_NAME_DEV: {os.getenv('DB_NAME_DEV')}")
    print()

    try:
        # Import and test database manager
        from models.database.connection_manager import get_db_manager

        db_manager = get_db_manager()

        print("Database Manager Configuration:")
        print(f"Using MySQL: True")
        print(f"MySQL Host: {db_manager.config.host}")
        print(f"MySQL Port: {db_manager.config.port}")
        print(f"MySQL Database: {db_manager.config.database}")
        print(f"MySQL User: {db_manager.config.username}")
        print()

        print("Testing database connection...")
        if db_manager.test_connection():
            print("✓ Database connection successful!")

            # Get table information
            table_info = db_manager.get_table_info()
            print(f"\nAvailable tables: {len(table_info)}")

            # Show first few tables with row counts
            count = 0
            for table_name, info in table_info.items():
                if count < 5:
                    print(f"  - {table_name}: {info.get('row_count', 0)} rows")
                    count += 1
                else:
                    break

            if len(table_info) > 5:
                print(f"  ... and {len(table_info) - 5} more tables")

            print()
            print("============================================================")
            print("✓ YOUR APP IS NOW USING MYSQL DATABASE!")
            print(f"✓ Connected to: {db_manager.config.host}:{db_manager.config.port}")
            print(f"✓ Database: {db_manager.config.database}")
            print("============================================================")

            return True
        else:
            print("✗ Database connection failed!")
            return False

    except Exception as e:
        print(f"✗ App database configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_app_database_config()
    sys.exit(0 if success else 1)
