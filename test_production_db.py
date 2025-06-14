#!/usr/bin/env python3
"""
Test script to verify production database connection
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.database import get_database_config, test_connection

def test_production_database():
    """Test production database connection"""

    print("="*60)
    print("PRODUCTION DATABASE CONNECTION TEST")
    print("="*60)

    # Force production environment
    os.environ['FLASK_ENV'] = 'production'

    # Get production database configuration
    config = get_database_config('production')

    print(f"Environment: production")
    print(f"Database Host: {config.host}")
    print(f"Database Port: {config.port}")
    print(f"Database Name: {config.database}")
    print(f"Database User: {config.username}")
    print(f"SSL Disabled: {config.ssl_disabled}")
    print(f"Auth Plugin: {config.auth_plugin}")

    print(f"\nTesting connection to production database...")

    if test_connection(config):
        print("✅ Production database connection successful!")
        return True
    else:
        print("❌ Production database connection failed!")
        print("\nTroubleshooting tips:")
        print("1. Ensure the MySQL server is running at 213.91.178.104:3306")
        print("2. Verify the database 'nutri_tracker_prod' exists")
        print("3. Check that user 'remote_user' has access to the production database")
        print("4. Ensure the user is configured with mysql_native_password authentication")
        return False

if __name__ == "__main__":
    success = test_production_database()
    sys.exit(0 if success else 1)
