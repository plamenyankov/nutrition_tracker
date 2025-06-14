"""
Environment configuration for development and production
"""
import os

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

# SQLite Configuration (for migration source)
SQLITE_CONFIG = {
    'local_path': os.getenv('LOCAL_SQLITE_PATH', 'database.db'),
    'production_path': os.getenv('PROD_SQLITE_PATH', '/root/nutrition_tracker_data/database.db'),
}

# Feature Flags
USE_MYSQL = os.getenv('USE_MYSQL', 'true').lower() == 'true'

# Application Configuration
APP_CONFIG = {
    'secret_key': os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production'),
    'debug': os.getenv('DEBUG', 'true' if IS_DEVELOPMENT else 'false').lower() == 'true',
    'session_timeout': int(os.getenv('SESSION_TIMEOUT', '30')),
}

def get_current_database_name():
    """Get the current database name based on environment"""
    if IS_PRODUCTION:
        return DB_CONFIG['prod_database']
    else:
        return DB_CONFIG['dev_database']

def get_sqlite_source_path():
    """Get the SQLite database path to migrate from"""
    if IS_PRODUCTION:
        return SQLITE_CONFIG['production_path']
    else:
        return SQLITE_CONFIG['local_path']
