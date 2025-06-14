#!/usr/bin/env python3
"""
Production Environment Setup Script
Run this script on your production server to create the .env file
"""

import os
import secrets
import shutil
from datetime import datetime

def create_production_env():
    """Create production .env file with proper configuration"""

    print("=" * 60)
    print("PRODUCTION ENVIRONMENT SETUP")
    print("=" * 60)

    # Check if .env already exists
    if os.path.exists('.env'):
        print("⚠️  .env file already exists!")
        response = input("Do you want to overwrite it? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("Aborted.")
            return False

        # Backup existing .env
        backup_name = f".env.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2('.env', backup_name)
        print(f"✓ Backup created: {backup_name}")

    # Get configuration values
    print("\nEnter production configuration:")
    print("(Press Enter to use default values shown in brackets)")

    # Database configuration
    db_host = input("Database Host [192.168.11.1]: ").strip() or "192.168.11.1"
    db_port = input("Database Port [3306]: ").strip() or "3306"
    db_user = input("Database User [remote_user]: ").strip() or "remote_user"

    # Password (hidden input would be better, but keeping it simple)
    db_pass = input("Database Password [BuGr@d@N4@loB6!]: ").strip() or "BuGr@d@N4@loB6!"

    # Database names
    db_name_prod = input("Production Database Name [nutri_tracker_prod]: ").strip() or "nutri_tracker_prod"
    db_name_dev = input("Development Database Name [nutri_tracker_dev]: ").strip() or "nutri_tracker_dev"

    # Generate secure secret key
    secret_key = secrets.token_urlsafe(32)

    # Create .env content
    env_content = f"""# Production Environment Configuration
FLASK_ENV=production
DEBUG=false
USE_MYSQL=true

# Remote MySQL Database Configuration
DB_HOST={db_host}
DB_PORT={db_port}
DB_USER={db_user}
DB_PASS={db_pass}
DB_NAME_DEV={db_name_dev}
DB_NAME_PROD={db_name_prod}

# SQLite fallback (for migration source if needed)
DATABASE_PATH=database.db

# Production Application Settings
SECRET_KEY={secret_key}
SESSION_TIMEOUT=30

# Security Settings
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=Lax

# Optional: OpenAI API Key (add if needed)
# OPENAI_API_KEY=your_openai_api_key_here
"""

    # Write .env file
    try:
        with open('.env', 'w') as f:
            f.write(env_content)

        # Set proper permissions (owner read/write only)
        os.chmod('.env', 0o600)

        print("✓ Production .env file created")
        print("✓ File permissions set to 600 (owner read/write only)")
        print(f"✓ Secure SECRET_KEY generated: {secret_key[:10]}...")

    except Exception as e:
        print(f"✗ Error creating .env file: {e}")
        return False

    print("\n" + "=" * 60)
    print("✓ Production environment setup complete!")
    print("\nNext steps:")
    print("1. Review the .env file and adjust any settings as needed")
    print("2. Test the database connection: python3 test_mysql_connection.py")
    print("3. Verify app configuration: python3 test_app_mysql.py")
    print("4. Run migration if needed: python3 migrate_to_mysql.py --full-migration")
    print("=" * 60)

    return True

def show_env_template():
    """Show the template for manual creation"""

    print("=" * 60)
    print("MANUAL .env FILE TEMPLATE")
    print("=" * 60)
    print("Copy and paste this template into your .env file:")
    print()

    secret_key = secrets.token_urlsafe(32)

    template = f"""# Production Environment Configuration
FLASK_ENV=production
DEBUG=false
USE_MYSQL=true

# Remote MySQL Database Configuration
DB_HOST=192.168.11.1
DB_PORT=3306
DB_USER=remote_user
DB_PASS=BuGr@d@N4@loB6!
DB_NAME_DEV=nutri_tracker_dev
DB_NAME_PROD=nutri_tracker_prod

# SQLite fallback (for migration source if needed)
DATABASE_PATH=database.db

# Production Application Settings
SECRET_KEY={secret_key}
SESSION_TIMEOUT=30

# Security Settings
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=Lax

# Optional: OpenAI API Key (add if needed)
# OPENAI_API_KEY=your_openai_api_key_here
"""

    print(template)
    print("=" * 60)
    print("After creating the file, set proper permissions:")
    print("chmod 600 .env")
    print("=" * 60)

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--template":
        show_env_template()
    else:
        create_production_env()
