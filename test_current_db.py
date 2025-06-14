#!/usr/bin/env python3
"""
Test current environment database connection
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.database import get_database_config, test_connection

def test_current_database():
    """Test connection to current environment database"""

    # Get current environment
    env = os.getenv('FLASK_ENV', 'development')

    print(f"Testing {env} database connection...")

    # Get database configuration for current environment
    config = get_database_config(env)

    print(f"Host: {config.host}")
    print(f"Port: {config.port}")
    print(f"Database: {config.database}")
    print(f"User: {config.username}")

    # Test connection
    if test_connection(config):
        print(f"✓ {env.title()} database connection successful")
        return True
    else:
        print(f"✗ {env.title()} database connection failed")
        return False

if __name__ == "__main__":
    success = test_current_database()
    sys.exit(0 if success else 1)
