#!/usr/bin/env python3
"""
Test MySQL connection and setup databases
"""

import os
import sys
import mysql.connector
from mysql.connector import Error

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.database import get_database_config, ensure_database_exists, test_connection

def test_remote_mysql_connection():
    """Test connection to remote MySQL server and create databases"""

    print("="*60)
    print("MySQL Connection Test")
    print("="*60)

    # Test for development environment
    print("\n1. Testing Development Environment")
    os.environ['FLASK_ENV'] = 'development'
    dev_config = get_database_config('development')

    print(f"Host: {dev_config.host}")
    print(f"Port: {dev_config.port}")
    print(f"Database: {dev_config.database}")
    print(f"User: {dev_config.username}")

    # Ensure database exists
    print(f"\nCreating database '{dev_config.database}' if it doesn't exist...")
    if ensure_database_exists(dev_config):
        print("✓ Database ready")
    else:
        print("✗ Failed to create database")
        return False

    # Test connection
    print("\nTesting connection...")
    if test_connection(dev_config):
        print("✓ Development database connection successful")
    else:
        print("✗ Development database connection failed")
        return False

    # Test for production environment
    print("\n2. Testing Production Environment")
    os.environ['FLASK_ENV'] = 'production'
    prod_config = get_database_config('production')

    print(f"Host: {prod_config.host}")
    print(f"Port: {prod_config.port}")
    print(f"Database: {prod_config.database}")
    print(f"User: {prod_config.username}")

    # Ensure database exists
    print(f"\nCreating database '{prod_config.database}' if it doesn't exist...")
    if ensure_database_exists(prod_config):
        print("✓ Database ready")
    else:
        print("✗ Failed to create database")
        return False

    # Test connection
    print("\nTesting connection...")
    if test_connection(prod_config):
        print("✓ Production database connection successful")
    else:
        print("✗ Production database connection failed")
        return False

    # Show database list
    print("\n3. Available Databases")
    try:
        connection = mysql.connector.connect(
            host=dev_config.host,
            port=dev_config.port,
            user=dev_config.username,
            password=dev_config.password,
            ssl_disabled=dev_config.ssl_disabled
        )

        cursor = connection.cursor()
        cursor.execute("SHOW DATABASES")
        databases = cursor.fetchall()

        print("Databases on server:")
        for (db,) in databases:
            if 'nutri' in db.lower():
                print(f"  - {db} ✓")
            else:
                print(f"  - {db}")

        cursor.close()
        connection.close()

    except Error as e:
        print(f"Error listing databases: {e}")

    print("\n" + "="*60)
    print("✓ All tests passed! Ready for migration.")
    print("="*60)

    # Show Docker configuration if running in Docker
    if os.path.exists('/.dockerenv'):
        print("\n⚠️  Running in Docker container")
        print("Make sure docker-compose.yml has proper network configuration:")
        print("  - extra_hosts: host.docker.internal:host-gateway")
        print("  - Or use network_mode: host")

    return True

if __name__ == "__main__":
    success = test_remote_mysql_connection()
    sys.exit(0 if success else 1)
