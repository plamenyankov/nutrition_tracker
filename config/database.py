import os
import logging
from dataclasses import dataclass
from typing import Optional
import mysql.connector
from mysql.connector import Error

logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """Database configuration for different environments"""
    host: str
    port: int
    database: str
    username: str
    password: str
    charset: str = 'utf8mb4'
    ssl_disabled: bool = True
    pool_size: int = 10
    max_overflow: int = 5
    pool_timeout: int = 30
    pool_recycle: int = 3600
    autocommit: bool = False
    auth_plugin: str = 'mysql_native_password'

def get_database_config(environment: str = None) -> DatabaseConfig:
    """Get database configuration based on environment"""
    env = environment or os.getenv('FLASK_ENV', 'development')

    # Remote database credentials - different IPs for local vs production
    # Local (with Wireguard): 192.168.11.1
    # Production (direct): 213.91.178.104
    if env == 'production':
        # Production uses direct internet connection
        db_host = os.getenv('DB_HOST', '213.91.178.104')
    else:
        # Development uses Wireguard VPN
        db_host = os.getenv('DB_HOST_LOCAL', '192.168.11.1')

    db_port = int(os.getenv('DB_PORT', '3306'))
    db_user = os.getenv('DB_USER', 'remote_user')
    db_pass = os.getenv('DB_PASS', 'BuGr@d@N4@loB6!')

    # Determine database name based on environment
    if env == 'production':
        db_name = os.getenv('DB_NAME_PROD', 'nutri_tracker_prod')
    else:  # development
        db_name = os.getenv('DB_NAME_DEV', 'nutri_tracker_dev')

    # Handle Docker network bridge
    if os.path.exists('/.dockerenv'):
        # Running inside Docker
        docker_host = os.getenv('DOCKER_DB_HOST', db_host)
        db_host = docker_host
        logger.info(f"Running in Docker, using host: {db_host}")

    return DatabaseConfig(
        host=db_host,
        port=db_port,
        database=db_name,
        username=db_user,
        password=db_pass,
        ssl_disabled=True,  # Disable SSL for internal network
        autocommit=False,
        auth_plugin='mysql_native_password'
    )

def ensure_database_exists(config: DatabaseConfig) -> bool:
    """Check if the database exists (assumes it's already created)"""
    try:
        # Try to connect directly to the database
        connection = mysql.connector.connect(
            host=config.host,
            port=config.port,
            database=config.database,
            user=config.username,
            password=config.password,
            ssl_disabled=config.ssl_disabled,
            auth_plugin=config.auth_plugin,
            connection_timeout=10
        )

        if connection.is_connected():
            logger.info(f"Database '{config.database}' is accessible")
            connection.close()
            return True

    except Error as e:
        if "Unknown database" in str(e):
            logger.error(f"Database '{config.database}' does not exist. Please create it first using setup_mysql_databases.py")
        elif "Authentication plugin" in str(e) or "Authentication requires secure connection" in str(e):
            logger.error(f"Authentication error: {e}")
            logger.error("The MySQL user may need to be configured with mysql_native_password authentication")
        elif "Access denied" in str(e):
            logger.error(f"Access denied: {e}")
            logger.error("Check username, password, and user permissions")
        else:
            logger.error(f"Failed to connect to database: {e}")
        return False

def get_connection_string(config: DatabaseConfig) -> str:
    """Generate MySQL connection string"""
    ssl_param = "&ssl_disabled=true" if config.ssl_disabled else ""
    auth_param = f"&auth_plugin={config.auth_plugin}" if config.auth_plugin else ""
    return (
        f"mysql+pymysql://{config.username}:{config.password}@"
        f"{config.host}:{config.port}/{config.database}"
        f"?charset={config.charset}{ssl_param}{auth_param}"
    )

def test_connection(config: DatabaseConfig) -> bool:
    """Test database connection"""
    try:
        connection = mysql.connector.connect(
            host=config.host,
            port=config.port,
            database=config.database,
            user=config.username,
            password=config.password,
            ssl_disabled=config.ssl_disabled,
            auth_plugin=config.auth_plugin,
            connection_timeout=10
        )

        if connection.is_connected():
            db_info = connection.get_server_info()
            logger.info(f"Successfully connected to MySQL Server version {db_info}")

            cursor = connection.cursor()
            cursor.execute("SELECT DATABASE();")
            record = cursor.fetchone()
            logger.info(f"Connected to database: {record[0]}")

            cursor.close()
            connection.close()
            return True

    except Error as e:
        logger.error(f"Error while connecting to MySQL: {e}")
        if "Authentication plugin" in str(e):
            logger.error("The MySQL user needs to be configured with mysql_native_password authentication")
        elif "Access denied" in str(e):
            logger.error("Check username, password, and user permissions")
        return False

    return False
