#!/usr/bin/env python3
"""
Setup MySQL databases on remote server
This script connects as a privileged user to create the required databases
"""

import os
import sys
import mysql.connector
from mysql.connector import Error
import getpass

def create_databases():
    """Create the required databases on the remote MySQL server"""

    print("="*60)
    print("MySQL Database Setup")
    print("="*60)

    # Get connection details
    host = input("MySQL Host [192.168.11.1]: ").strip() or "192.168.11.1"
    port = int(input("MySQL Port [3306]: ").strip() or "3306")

    print("\nEnter MySQL admin credentials (user with CREATE DATABASE privileges):")
    admin_user = input("Admin Username [root]: ").strip() or "root"
    admin_password = getpass.getpass("Admin Password: ")

    # Database names
    dev_db = "nutri_tracker_dev"
    prod_db = "nutri_tracker_prod"

    # Application user details
    app_user = "remote_user"
    app_password = "BuGr@d@N4@loB6!"

    try:
        # Connect as admin
        print(f"\nConnecting to MySQL server at {host}:{port}...")
        connection = mysql.connector.connect(
            host=host,
            port=port,
            user=admin_user,
            password=admin_password,
            ssl_disabled=True,
            auth_plugin='mysql_native_password'
        )

        if connection.is_connected():
            cursor = connection.cursor()

            print("✓ Connected successfully")

            # Create databases
            print(f"\nCreating database: {dev_db}")
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{dev_db}` "
                          f"DEFAULT CHARACTER SET utf8mb4 "
                          f"COLLATE utf8mb4_unicode_ci")
            print("✓ Development database created")

            print(f"\nCreating database: {prod_db}")
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{prod_db}` "
                          f"DEFAULT CHARACTER SET utf8mb4 "
                          f"COLLATE utf8mb4_unicode_ci")
            print("✓ Production database created")

                        # Create/update application user
            print(f"\nSetting up application user: {app_user}")

            # Create user if not exists with native password authentication
            try:
                cursor.execute(f"CREATE USER IF NOT EXISTS '{app_user}'@'%' IDENTIFIED WITH mysql_native_password BY '{app_password}'")
                print("✓ Application user created/updated with native password authentication")
            except Error as e:
                if "already exists" in str(e).lower():
                    print("✓ Application user already exists")
                    # Try to alter existing user to use native password
                    try:
                        cursor.execute(f"ALTER USER '{app_user}'@'%' IDENTIFIED WITH mysql_native_password BY '{app_password}'")
                        print("✓ Updated existing user to use native password authentication")
                    except Error as e2:
                        print(f"Warning: Could not update authentication method: {e2}")
                else:
                    print(f"Warning: {e}")

            # Grant privileges on development database
            cursor.execute(f"GRANT ALL PRIVILEGES ON `{dev_db}`.* TO '{app_user}'@'%'")
            print(f"✓ Granted privileges on {dev_db}")

            # Grant privileges on production database
            cursor.execute(f"GRANT ALL PRIVILEGES ON `{prod_db}`.* TO '{app_user}'@'%'")
            print(f"✓ Granted privileges on {prod_db}")

            # Flush privileges
            cursor.execute("FLUSH PRIVILEGES")
            print("✓ Privileges flushed")

            # Show created databases
            print("\nVerifying databases:")
            cursor.execute("SHOW DATABASES LIKE 'nutri_tracker_%'")
            databases = cursor.fetchall()

            for (db_name,) in databases:
                print(f"  - {db_name} ✓")

            # Test application user connection
            print(f"\nTesting application user connection...")
            test_connection = mysql.connector.connect(
                host=host,
                port=port,
                user=app_user,
                password=app_password,
                database=dev_db,
                ssl_disabled=True,
                auth_plugin='mysql_native_password'
            )

            if test_connection.is_connected():
                print("✓ Application user can connect to development database")
                test_connection.close()

            test_connection = mysql.connector.connect(
                host=host,
                port=port,
                user=app_user,
                password=app_password,
                database=prod_db,
                ssl_disabled=True,
                auth_plugin='mysql_native_password'
            )

            if test_connection.is_connected():
                print("✓ Application user can connect to production database")
                test_connection.close()

            cursor.close()
            connection.close()

            print("\n" + "="*60)
            print("✓ Database setup completed successfully!")
            print("="*60)
            print("\nYou can now run the migration:")
            print("python test_mysql_connection.py")
            print("python migrate_to_mysql.py")

            return True

    except Error as e:
        print(f"\n✗ Error: {e}")
        return False

    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user")
        return False

def show_manual_setup():
    """Show manual SQL commands for database setup"""
    print("\n" + "="*60)
    print("MANUAL SETUP (if you prefer to run SQL commands directly)")
    print("="*60)

    sql_commands = """
-- Connect to MySQL as admin user (root)
mysql -h 192.168.11.1 -P 3306 -u root -p

-- Create databases
CREATE DATABASE IF NOT EXISTS `nutri_tracker_dev`
    DEFAULT CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS `nutri_tracker_prod`
    DEFAULT CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- Create application user with native password authentication
CREATE USER IF NOT EXISTS 'remote_user'@'%' IDENTIFIED WITH mysql_native_password BY 'BuGr@d@N4@loB6!';

-- Grant privileges
GRANT ALL PRIVILEGES ON `nutri_tracker_dev`.* TO 'remote_user'@'%';
GRANT ALL PRIVILEGES ON `nutri_tracker_prod`.* TO 'remote_user'@'%';

-- Flush privileges
FLUSH PRIVILEGES;

-- Verify setup
SHOW DATABASES LIKE 'nutri_tracker_%';
SELECT User, Host FROM mysql.user WHERE User = 'remote_user';
"""

    print(sql_commands)

if __name__ == "__main__":
    print("Choose setup method:")
    print("1. Automated setup (recommended)")
    print("2. Show manual SQL commands")

    choice = input("\nEnter choice (1 or 2): ").strip()

    if choice == "2":
        show_manual_setup()
    else:
        success = create_databases()
        if not success:
            print("\nIf automated setup failed, you can use manual setup:")
            show_manual_setup()

        sys.exit(0 if success else 1)
