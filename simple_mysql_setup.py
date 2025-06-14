#!/usr/bin/env python3
"""
Simple MySQL database setup for direct connection
This script creates the required databases and configures the user properly
"""

import os
import sys
import mysql.connector
from mysql.connector import Error
import getpass

def setup_mysql_databases():
    """Setup MySQL databases with proper authentication"""

    print("="*60)
    print("Simple MySQL Database Setup")
    print("="*60)
    print("This script will create the required databases and configure the user")
    print("for direct connection (no SSH tunnel needed)")

    # Get connection details
    host = input("MySQL Host [192.168.11.1]: ").strip() or "192.168.11.1"
    port = int(input("MySQL Port [3306]: ").strip() or "3306")

    print(f"\nConnecting to MySQL server at {host}:{port}")
    print("Enter MySQL admin credentials (user with CREATE DATABASE and CREATE USER privileges):")
    admin_user = input("Admin Username [root]: ").strip() or "root"
    admin_password = getpass.getpass("Admin Password: ")

    # Database and user details
    dev_db = "nutri_tracker_dev"
    prod_db = "nutri_tracker_prod"
    app_user = "remote_user"
    app_password = "BuGr@d@N4@loB6!"

    try:
        print(f"\nConnecting to MySQL server...")

        # Connect as admin (try different authentication methods)
        connection = None
        for auth_plugin in ['mysql_native_password', 'caching_sha2_password', None]:
            try:
                connect_params = {
                    'host': host,
                    'port': port,
                    'user': admin_user,
                    'password': admin_password,
                    'ssl_disabled': True,
                    'connection_timeout': 10
                }
                if auth_plugin:
                    connect_params['auth_plugin'] = auth_plugin

                connection = mysql.connector.connect(**connect_params)
                if connection.is_connected():
                    print(f"✓ Connected successfully using {auth_plugin or 'default'} authentication")
                    break
            except Error as e:
                if auth_plugin is None:  # Last attempt failed
                    raise e
                continue

        if not connection or not connection.is_connected():
            print("✗ Failed to connect with any authentication method")
            return False

        cursor = connection.cursor()

        # Create databases
        print(f"\n1. Creating databases...")

        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{dev_db}` "
                      f"DEFAULT CHARACTER SET utf8mb4 "
                      f"COLLATE utf8mb4_unicode_ci")
        print(f"✓ Created database: {dev_db}")

        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{prod_db}` "
                      f"DEFAULT CHARACTER SET utf8mb4 "
                      f"COLLATE utf8mb4_unicode_ci")
        print(f"✓ Created database: {prod_db}")

        # Handle user creation/update
        print(f"\n2. Setting up application user: {app_user}")

        # Check if user exists
        cursor.execute("SELECT User, Host, plugin FROM mysql.user WHERE User = %s", (app_user,))
        existing_users = cursor.fetchall()

        if existing_users:
            print(f"✓ User '{app_user}' already exists")
            for user, host, plugin in existing_users:
                print(f"  - {user}@{host} using {plugin} authentication")

            # Update existing user to use native password
            print(f"Updating user to use mysql_native_password authentication...")
            cursor.execute(f"ALTER USER '{app_user}'@'%' IDENTIFIED WITH mysql_native_password BY '{app_password}'")
            print("✓ Updated user authentication method")
        else:
            # Create new user with native password
            print(f"Creating new user with mysql_native_password authentication...")
            cursor.execute(f"CREATE USER '{app_user}'@'%' IDENTIFIED WITH mysql_native_password BY '{app_password}'")
            print("✓ Created new user")

        # Grant privileges
        print(f"\n3. Granting privileges...")
        cursor.execute(f"GRANT ALL PRIVILEGES ON `{dev_db}`.* TO '{app_user}'@'%'")
        cursor.execute(f"GRANT ALL PRIVILEGES ON `{prod_db}`.* TO '{app_user}'@'%'")
        cursor.execute("FLUSH PRIVILEGES")
        print(f"✓ Granted privileges on both databases")

        # Verify setup
        print(f"\n4. Verifying setup...")
        cursor.execute("SHOW DATABASES LIKE 'nutri_tracker_%'")
        databases = cursor.fetchall()

        print("Created databases:")
        for (db_name,) in databases:
            print(f"  - {db_name}")

        # Test application user connection
        print(f"\n5. Testing application user connection...")

        for db_name in [dev_db, prod_db]:
            try:
                test_connection = mysql.connector.connect(
                    host=host,
                    port=port,
                    user=app_user,
                    password=app_password,
                    database=db_name,
                    ssl_disabled=True,
                    auth_plugin='mysql_native_password',
                    connection_timeout=10
                )

                if test_connection.is_connected():
                    print(f"✓ Application user can connect to {db_name}")
                    test_connection.close()
                else:
                    print(f"✗ Failed to connect to {db_name}")

            except Error as e:
                print(f"✗ Connection test failed for {db_name}: {e}")

        cursor.close()
        connection.close()

        print("\n" + "="*60)
        print("✓ MySQL setup completed successfully!")
        print("="*60)

        print(f"\nConfiguration summary:")
        print(f"Host: {host}:{port}")
        print(f"Databases: {dev_db}, {prod_db}")
        print(f"User: {app_user}")
        print(f"Authentication: mysql_native_password")

        print(f"\nNext steps:")
        print(f"1. Test connection: python test_mysql_connection.py")
        print(f"2. Run migration: python migrate_to_mysql.py")

        return True

    except Error as e:
        print(f"\n✗ Error: {e}")

        if "Access denied" in str(e):
            print("\nTroubleshooting:")
            print("- Check admin username and password")
            print("- Ensure admin user has CREATE DATABASE and CREATE USER privileges")
        elif "Can't connect" in str(e):
            print("\nTroubleshooting:")
            print("- Check if MySQL server is running")
            print("- Verify host and port are correct")
            print("- Check firewall settings")

        return False

    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user")
        return False

if __name__ == "__main__":
    success = setup_mysql_databases()
    sys.exit(0 if success else 1)
