#!/usr/bin/env python3
"""
Simple database connection test for Docker entrypoint
"""
import os
import sys
import mysql.connector
from mysql.connector import Error

def test_mysql_connection():
    """Test MySQL connection with current environment variables"""

    # Get connection parameters from environment
    host = os.getenv('DB_HOST', 'localhost')
    port = int(os.getenv('DB_PORT', '3306'))
    user = os.getenv('DB_USER', 'root')
    password = os.getenv('DB_PASS', '')

    # Determine database based on environment
    if os.getenv('FLASK_ENV') == 'production':
        database = os.getenv('DB_NAME_PROD', 'nutri_tracker_prod')
    else:
        database = os.getenv('DB_NAME_DEV', 'nutri_tracker_dev')

    print(f"Testing production database connection...")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Database: {database}")
    print(f"User: {user}")

    try:
        # Test connection
        connection = mysql.connector.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            ssl_disabled=True,
            auth_plugin='mysql_native_password',
            connection_timeout=10
        )

        if connection.is_connected():
            print("✓ Database connection successful!")

                        # Test a simple query
            cursor = connection.cursor()
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()

            cursor.close()
            connection.close()

            if result:
                print("✓ Database query test successful!")
                return True
            else:
                print("✗ Database query test failed!")
                return False

    except Error as e:
        print(f"✗ Database connection failed: {e}")

        # Provide helpful error messages
        if "Access denied" in str(e):
            print("  → Check username and password")
        elif "Unknown database" in str(e):
            print(f"  → Database '{database}' does not exist")
        elif "Can't connect to MySQL server" in str(e):
            print(f"  → MySQL server at {host}:{port} is not reachable")
        elif "Authentication plugin" in str(e):
            print("  → User needs mysql_native_password authentication")

        return False

    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_mysql_connection()
    sys.exit(0 if success else 1)
