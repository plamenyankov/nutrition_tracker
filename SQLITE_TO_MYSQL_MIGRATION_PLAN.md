# SQLite to MySQL Migration Plan

## Overview
This document outlines a comprehensive plan for migrating the nutrition tracker application from SQLite to MySQL, establishing separate development and production databases with proper configuration management.

## Current State Analysis

### Current Database Setup
- **Database Type**: SQLite
- **Location**: `database.db` (local file)
- **Connection**: Direct file-based connections via `sqlite3` module
- **Environment**: Single database for all environments
- **Configuration**: Hardcoded paths with basic environment variable support

### Current Database Usage Patterns
- **Models using SQLite**:
  - `models/food.py` - FoodDatabase class
  - `models/calorie_weight.py` - CalorieWeight class
  - `models/services/progression_service.py` - ProgressionService
  - `models/services/gym_service.py` - GymService
  - All monitoring and security services

### Current Tables (from analysis)
- Nutrition tables: `Ingredient`, `Unit`, `Nutrition`, `Ingredient_Quantity`, `Consumption`
- Recipe tables: `Recipe`, `Recipe_Ingredients`, `recipe_consumption`
- Gym tables: `exercises`, `workout_sessions`, `workout_sets`, `progression_history`
- Monitoring tables: `performance_metrics`, `metrics`, `alerts`, `health_checks`
- Security tables: `user_sessions`, `failed_login_attempts`, `audit_logs`
- User tables: `users`, `Favorites`

## Migration Strategy

### Phase 1: Infrastructure Setup (Week 1)

#### 1.1 MySQL Server Setup

**Development Environment:**
```bash
# Local MySQL installation (macOS)
brew install mysql
brew services start mysql

# Create development database
mysql -u root -p
CREATE DATABASE nutrition_tracker_dev;
CREATE USER 'nutrition_dev'@'localhost' IDENTIFIED BY 'dev_password_123';
GRANT ALL PRIVILEGES ON nutrition_tracker_dev.* TO 'nutrition_dev'@'localhost';
FLUSH PRIVILEGES;
```

**Production Environment (DigitalOcean):**
```bash
# Option 1: DigitalOcean Managed MySQL Database
# - Create managed MySQL cluster via DigitalOcean control panel
# - Configure connection pooling and SSL

# Option 2: Self-hosted MySQL on existing droplet
apt-get update
apt-get install mysql-server
mysql_secure_installation

# Create production database
mysql -u root -p
CREATE DATABASE nutrition_tracker_prod;
CREATE USER 'nutrition_prod'@'%' IDENTIFIED BY 'STRONG_PRODUCTION_PASSWORD';
GRANT ALL PRIVILEGES ON nutrition_tracker_prod.* TO 'nutrition_prod'@'%';
FLUSH PRIVILEGES;
```

#### 1.2 Database Configuration Management

**Create `config/database.py`:**
```python
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class DatabaseConfig:
    """Database configuration for different environments"""
    host: str
    port: int
    database: str
    username: str
    password: str
    charset: str = 'utf8mb4'
    ssl_disabled: bool = False
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600

def get_database_config(environment: str = None) -> DatabaseConfig:
    """Get database configuration based on environment"""
    env = environment or os.getenv('FLASK_ENV', 'development')

    if env == 'production':
        return DatabaseConfig(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            port=int(os.getenv('MYSQL_PORT', 3306)),
            database=os.getenv('MYSQL_DATABASE', 'nutrition_tracker_prod'),
            username=os.getenv('MYSQL_USER', 'nutrition_prod'),
            password=os.getenv('MYSQL_PASSWORD'),
            ssl_disabled=os.getenv('MYSQL_SSL_DISABLED', 'false').lower() == 'true'
        )
    else:  # development
        return DatabaseConfig(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            port=int(os.getenv('MYSQL_PORT', 3306)),
            database=os.getenv('MYSQL_DATABASE', 'nutrition_tracker_dev'),
            username=os.getenv('MYSQL_USER', 'nutrition_dev'),
            password=os.getenv('MYSQL_PASSWORD', 'dev_password_123'),
            ssl_disabled=True  # Disable SSL for local development
        )

def get_connection_string(config: DatabaseConfig) -> str:
    """Generate MySQL connection string"""
    ssl_param = "&ssl_disabled=true" if config.ssl_disabled else ""
    return (
        f"mysql+pymysql://{config.username}:{config.password}@"
        f"{config.host}:{config.port}/{config.database}"
        f"?charset={config.charset}{ssl_param}"
    )
```

### Phase 2: Database Abstraction Layer (Week 2)

#### 2.1 Create Database Connection Manager

**Create `models/database/connection_manager.py`:**
```python
import mysql.connector
from mysql.connector import pooling
import sqlite3
import os
import logging
from contextlib import contextmanager
from typing import Optional, Union
from config.database import get_database_config, DatabaseConfig

logger = logging.getLogger(__name__)

class DatabaseConnectionManager:
    """Unified database connection manager supporting both SQLite and MySQL"""

    def __init__(self, use_mysql: bool = None):
        self.use_mysql = use_mysql if use_mysql is not None else os.getenv('USE_MYSQL', 'false').lower() == 'true'
        self.config = get_database_config() if self.use_mysql else None
        self.connection_pool = None

        if self.use_mysql:
            self._init_mysql_pool()

    def _init_mysql_pool(self):
        """Initialize MySQL connection pool"""
        try:
            pool_config = {
                'pool_name': 'nutrition_tracker_pool',
                'pool_size': self.config.pool_size,
                'pool_reset_session': True,
                'host': self.config.host,
                'port': self.config.port,
                'database': self.config.database,
                'user': self.config.username,
                'password': self.config.password,
                'charset': self.config.charset,
                'autocommit': False,
                'time_zone': '+00:00'
            }

            if not self.config.ssl_disabled:
                pool_config['ssl_disabled'] = False

            self.connection_pool = pooling.MySQLConnectionPool(**pool_config)
            logger.info("MySQL connection pool initialized successfully")

        except mysql.connector.Error as e:
            logger.error(f"Failed to initialize MySQL connection pool: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """Get database connection (context manager)"""
        if self.use_mysql:
            connection = None
            try:
                connection = self.connection_pool.get_connection()
                yield connection
            except mysql.connector.Error as e:
                if connection:
                    connection.rollback()
                logger.error(f"MySQL connection error: {e}")
                raise
            finally:
                if connection and connection.is_connected():
                    connection.close()
        else:
            # SQLite fallback
            db_path = os.getenv('DATABASE_PATH', 'database.db')
            connection = sqlite3.connect(db_path)
            try:
                connection.execute("PRAGMA journal_mode=WAL")
                connection.execute("PRAGMA foreign_keys=ON")
                yield connection
            except sqlite3.Error as e:
                connection.rollback()
                logger.error(f"SQLite connection error: {e}")
                raise
            finally:
                connection.close()

    def execute_query(self, query: str, params: tuple = None, fetch_one: bool = False, fetch_all: bool = False):
        """Execute query with automatic connection management"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                if fetch_one:
                    result = cursor.fetchone()
                elif fetch_all:
                    result = cursor.fetchall()
                else:
                    result = cursor.rowcount

                conn.commit()
                return result

            except Exception as e:
                conn.rollback()
                logger.error(f"Query execution error: {e}")
                raise
            finally:
                cursor.close()

# Global connection manager instance
db_manager = DatabaseConnectionManager()
```

### Phase 3: Migration Tools (Week 3)

#### 3.1 Create Schema Migration Tool

**Create `migrations/schema_migrator.py`:**
```python
import os
import sqlite3
import mysql.connector
import logging
from typing import List, Dict, Any
from models.database.connection_manager import DatabaseConnectionManager

logger = logging.getLogger(__name__)

class SchemaMigrator:
    """Tool to migrate schema from SQLite to MySQL"""

    def __init__(self):
        self.sqlite_path = os.getenv('DATABASE_PATH', 'database.db')
        self.mysql_manager = DatabaseConnectionManager(use_mysql=True)

    def extract_sqlite_schema(self) -> Dict[str, Any]:
        """Extract complete schema from SQLite database"""
        schema = {'tables': {}, 'indexes': []}

        with sqlite3.connect(self.sqlite_path) as conn:
            cursor = conn.cursor()

            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = cursor.fetchall()

            for (table_name,) in tables:
                # Get table schema
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()

                # Get foreign keys
                cursor.execute(f"PRAGMA foreign_key_list({table_name})")
                foreign_keys = cursor.fetchall()

                schema['tables'][table_name] = {
                    'columns': columns,
                    'foreign_keys': foreign_keys
                }

            # Get indexes
            cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'")
            schema['indexes'] = cursor.fetchall()

        return schema

    def create_mysql_schema(self, schema: Dict[str, Any]) -> List[str]:
        """Create MySQL schema from SQLite schema"""
        sql_statements = []

        # Create tables
        for table_name, table_info in schema['tables'].items():
            columns = []
            foreign_keys = []

            # Process columns
            for col_info in table_info['columns']:
                cid, name, type_name, notnull, default_value, pk = col_info
                col_def = self._convert_column_definition(type_name, notnull, default_value, pk)
                columns.append(f"{name} {col_def}")

            # Process foreign keys
            for fk_info in table_info['foreign_keys']:
                id, seq, table, from_col, to_col, on_update, on_delete, match = fk_info
                foreign_keys.append(f"FOREIGN KEY ({from_col}) REFERENCES {table}({to_col})")

            # Generate CREATE TABLE statement
            all_definitions = columns + foreign_keys
            create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} (\n"
            create_sql += ",\n".join(f"    {definition}" for definition in all_definitions)
            create_sql += "\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"

            sql_statements.append(create_sql)

        return sql_statements

    def _convert_column_definition(self, sqlite_type: str, notnull: int, default_value: Any, is_pk: int) -> str:
        """Convert SQLite column definition to MySQL"""
        # Type mapping
        type_mapping = {
            'INTEGER': 'INT',
            'REAL': 'DECIMAL(10,2)',
            'TEXT': 'TEXT',
            'BLOB': 'BLOB',
            'BOOLEAN': 'BOOLEAN',
            'DATE': 'DATE',
            'DATETIME': 'DATETIME',
            'TIMESTAMP': 'TIMESTAMP',
            'VARCHAR(255)': 'VARCHAR(255)',
            'FLOAT': 'FLOAT',
            'TINYINT': 'TINYINT'
        }

        mysql_type = type_mapping.get(sqlite_type.upper(), sqlite_type)

        # Build definition
        definition = mysql_type

        if is_pk:
            definition += " AUTO_INCREMENT PRIMARY KEY"
        elif notnull:
            definition += " NOT NULL"

        if default_value is not None and not is_pk:
            if isinstance(default_value, str):
                definition += f" DEFAULT '{default_value}'"
            else:
                definition += f" DEFAULT {default_value}"

        return definition

    def migrate_schema(self) -> bool:
        """Execute complete schema migration"""
        try:
            logger.info("Starting schema migration from SQLite to MySQL")

            # Extract SQLite schema
            schema = self.extract_sqlite_schema()
            logger.info(f"Extracted schema for {len(schema['tables'])} tables")

            # Generate MySQL schema
            sql_statements = self.create_mysql_schema(schema)

            # Execute MySQL schema creation
            with self.mysql_manager.get_connection() as conn:
                cursor = conn.cursor()

                for sql in sql_statements:
                    try:
                        cursor.execute(sql)
                        logger.debug(f"Executed: {sql[:100]}...")
                    except mysql.connector.Error as e:
                        logger.error(f"Failed to execute SQL: {sql[:100]}... Error: {e}")
                        raise

                conn.commit()

            logger.info("Schema migration completed successfully")
            return True

        except Exception as e:
            logger.error(f"Schema migration failed: {e}")
            return False
```

### Phase 4: Environment Configuration (Week 4)

#### 4.1 Update Requirements

**Update `requirements.txt`:**
```txt
flask
gunicorn
pandas
plotly
openai>=1.0.0
python-dotenv
flask-login
mysql-connector-python>=8.0.0
PyMySQL>=1.0.0
```

#### 4.2 Environment Files

**Create `.env.development`:**
```env
# Development Environment
FLASK_ENV=development
DEBUG=true
USE_MYSQL=true

# MySQL Development Database
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=nutrition_tracker_dev
MYSQL_USER=nutrition_dev
MYSQL_PASSWORD=dev_password_123
MYSQL_SSL_DISABLED=true

# Fallback SQLite
DATABASE_PATH=database.db
SECRET_KEY=development_secret_key
```

**Create `.env.production`:**
```env
# Production Environment
FLASK_ENV=production
DEBUG=false
USE_MYSQL=true

# MySQL Production Database
MYSQL_HOST=your-mysql-host.db.ondigitalocean.com
MYSQL_PORT=25060
MYSQL_DATABASE=nutrition_tracker_prod
MYSQL_USER=nutrition_prod
MYSQL_PASSWORD=your_strong_production_password
MYSQL_SSL_DISABLED=false

SECRET_KEY=your_super_secret_production_key
```

### Phase 5: Migration Execution Scripts

#### 5.1 Complete Migration Script

**Create `migrate_to_mysql.py`:**
```python
#!/usr/bin/env python3
"""Complete migration script from SQLite to MySQL"""
import os
import sys
import logging
from dotenv import load_dotenv
from migrations.schema_migrator import SchemaMigrator
from migrations.data_migrator import DataMigrator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Execute complete migration process"""

    # Load environment variables
    env_file = sys.argv[1] if len(sys.argv) > 1 else '.env.development'
    load_dotenv(env_file)

    logger.info(f"Starting migration with environment: {env_file}")

    try:
        # Step 1: Schema Migration
        logger.info("=== STEP 1: Schema Migration ===")
        schema_migrator = SchemaMigrator()

        if not schema_migrator.migrate_schema():
            logger.error("Schema migration failed!")
            return False

        # Step 2: Data Migration
        logger.info("=== STEP 2: Data Migration ===")
        data_migrator = DataMigrator()

        if not data_migrator.migrate_all_data():
            logger.error("Data migration failed!")
            return False

        # Step 3: Verification
        logger.info("=== STEP 3: Migration Verification ===")

        if not data_migrator.verify_migration():
            logger.error("Migration verification failed!")
            return False

        logger.info("=== MIGRATION COMPLETED SUCCESSFULLY ===")
        return True

    except Exception as e:
        logger.error(f"Migration failed with error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
```

### Phase 6: Deployment Strategy

#### 6.1 Development Migration

```bash
# 1. Backup current database
cp database.db database_backup_$(date +%Y%m%d_%H%M%S).db

# 2. Setup MySQL development
brew install mysql
brew services start mysql
mysql -u root -p < setup_dev_mysql.sql

# 3. Run migration
python migrate_to_mysql.py .env.development

# 4. Test application
export USE_MYSQL=true
python app.py
```

#### 6.2 Production Migration

```bash
# 1. Create production backup
ssh root@your-server "cp /root/nutrition_tracker_data/database.db /root/backups/"

# 2. Setup production MySQL (DigitalOcean managed database recommended)

# 3. Deploy updated code
git push origin main
ssh root@your-server "cd /root/nutrition_tracker && git pull"

# 4. Run production migration
ssh root@your-server "cd /root/nutrition_tracker && python migrate_to_mysql.py .env.production"

# 5. Update Docker configuration
ssh root@your-server "docker-compose down && docker-compose up -d"
```

## Risk Mitigation

### 1. Data Loss Prevention
- **Multiple Backups**: SQLite backup before migration
- **Verification Steps**: Row count verification, data integrity checks
- **Rollback Plan**: Quick revert to SQLite if issues occur

### 2. Downtime Minimization
- **Blue-Green Deployment**: Run both databases temporarily
- **Feature Flags**: Toggle between SQLite and MySQL
- **Health Checks**: Automated monitoring during migration

### 3. Performance Monitoring
- **Baseline Metrics**: Establish performance benchmarks
- **Real-time Monitoring**: Connection pool, query performance
- **Alerting**: Automated alerts for performance degradation

## Timeline Summary

| Week | Phase | Tasks | Deliverables |
|------|-------|-------|--------------|
| 1 | Infrastructure | MySQL setup, configuration | Dev/Prod databases ready |
| 2 | Abstraction | Connection manager, SQL builder | Database abstraction layer |
| 3 | Migration Tools | Schema/data migrators | Migration scripts |
| 4 | Code Updates | Model updates, environment config | Updated application code |
| 5 | Execution | Run migrations, testing | Migrated databases |
| 6 | Optimization | Monitoring, backup, tuning | Production-ready system |

## Success Criteria

### Technical
- ✅ Zero data loss during migration
- ✅ Application functionality unchanged
- ✅ Performance equal or better than SQLite
- ✅ Automated backup and monitoring

### Operational
- ✅ Separate dev/prod environments
- ✅ Easy rollback capability
- ✅ Comprehensive documentation
- ✅ Team training completed

This plan provides a comprehensive, phased approach to migrating from SQLite to MySQL while maintaining system reliability and minimizing risks.
