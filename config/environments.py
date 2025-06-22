"""
Environment configuration for development and production
"""
import os
from typing import Dict, Any

# Environment detection
FLASK_ENV = os.getenv('FLASK_ENV', 'development')
IS_PRODUCTION = FLASK_ENV == 'production'
IS_DEVELOPMENT = FLASK_ENV == 'development'

# Remote MySQL Database Configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', '192.168.11.1'),
    'port': int(os.getenv('DB_PORT', '3306')),
    'user': os.getenv('DB_USER', 'remote_user'),
    'password': os.getenv('DB_PASS', 'BuGr@d@N4@loB6!'),
    'dev_database': os.getenv('DB_NAME_DEV', 'nutri_tracker_dev'),
    'prod_database': os.getenv('DB_NAME_PROD', 'nutri_tracker_prod'),
}

# Docker Network Bridge Configuration
# If running in Docker, this should be the IP/hostname accessible from inside the container
DOCKER_DB_HOST = os.getenv('DOCKER_DB_HOST', 'host.docker.internal')

# Feature Flags
USE_MYSQL = os.getenv('USE_MYSQL', 'true').lower() == 'true'

def get_environment_config() -> Dict[str, Any]:
    """Get environment-specific configuration"""

    # MySQL-only configuration
    config = {
        'mysql': {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'port': int(os.getenv('MYSQL_PORT', 3306)),
            'database': os.getenv('MYSQL_DATABASE', 'nutrition_tracker'),
            'username': os.getenv('MYSQL_USERNAME', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'charset': os.getenv('MYSQL_CHARSET', 'utf8mb4'),
            'autocommit': os.getenv('MYSQL_AUTOCOMMIT', 'false').lower() == 'true',
            'pool_size': int(os.getenv('MYSQL_POOL_SIZE', 10)),
            'ssl_disabled': os.getenv('MYSQL_SSL_DISABLED', 'true').lower() == 'true'
        },
        'app': {
            'secret_key': os.getenv('SECRET_KEY', 'dev-key-change-in-production'),
            'debug': os.getenv('DEBUG', 'false').lower() == 'true',
            'flask_env': os.getenv('FLASK_ENV', 'production')
        }
    }

    return config

def get_database_environment():
    """Get database environment (always MySQL now)"""
    return 'mysql'

def get_current_database_name():
    """Get the current database name based on environment"""
    if IS_PRODUCTION:
        return DB_CONFIG['prod_database']
    else:
        return DB_CONFIG['dev_database']
