#!/usr/bin/env python3
"""
Complete migration script from SQLite to MySQL
Supports both local and production SQLite sources
Supports development and production MySQL targets
"""

import os
import sys
import logging
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from migrations.schema_migrator import SchemaMigrator
from migrations.data_migrator import DataMigrator
from config.database import test_connection, get_database_config
from models.database.connection_manager import get_db_manager

# Setup logging
def setup_logging(log_level='INFO'):
    """Setup logging configuration"""
    log_filename = f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler(sys.stdout)
        ]
    )

    return log_filename

logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Migrate SQLite database to remote MySQL'
    )

    parser.add_argument(
        '--env',
        choices=['development', 'production'],
        default='development',
        help='Environment to migrate to (default: development)'
    )

    parser.add_argument(
        '--source',
        choices=['local', 'production'],
        default='local',
        help='Source SQLite database (default: local)'
    )

    parser.add_argument(
        '--source-path',
        help='Custom path to source SQLite database'
    )

    parser.add_argument(
        '--schema-only',
        action='store_true',
        help='Only migrate schema, not data'
    )

    parser.add_argument(
        '--data-only',
        action='store_true',
        help='Only migrate data (assumes schema exists)'
    )

    parser.add_argument(
        '--drop-existing',
        action='store_true',
        help='Drop existing tables before migration'
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=1000,
        help='Batch size for data migration (default: 1000)'
    )

    parser.add_argument(
        '--tables',
        nargs='+',
        help='Specific tables to migrate (default: all)'
    )

    parser.add_argument(
        '--skip-verification',
        action='store_true',
        help='Skip verification after migration'
    )

    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )

    return parser.parse_args()

def test_mysql_connection():
    """Test MySQL connection before migration"""
    logger.info("Testing MySQL connection...")

    config = get_database_config()
    logger.info(f"Connecting to MySQL at {config.host}:{config.port}")
    logger.info(f"Database: {config.database}")

    if test_connection(config):
        logger.info("✓ MySQL connection successful")
        return True
    else:
        logger.error("✗ MySQL connection failed")
        return False

def get_source_sqlite_path(args):
    """Get the source SQLite database path"""
    if args.source_path:
        return args.source_path
    elif args.source == 'production':
        # In Docker container, the volume is mounted at /app/data
        if os.path.exists('/app/data/database.db'):
            return '/app/data/database.db'
        return os.getenv('PROD_SQLITE_PATH', '/root/nutrition_tracker_data/database.db')
    else:
        # Try multiple possible locations for local database
        possible_paths = [
            '/app/data/database.db',  # Docker volume mount
            'database.db',            # Current directory
            'database_old.db',        # Backup database
            '/app/database.db'        # App directory
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path

        return os.getenv('LOCAL_SQLITE_PATH', 'database.db')

def main():
    """Execute complete migration process"""

    # Parse arguments
    args = parse_arguments()

    # Setup logging
    log_filename = setup_logging(args.log_level)
    logger.info(f"Migration log: {log_filename}")

    # Load environment variables
    os.environ['FLASK_ENV'] = args.env
    env_file = f'.env.{args.env}' if os.path.exists(f'.env.{args.env}') else '.env'
    if os.path.exists(env_file):
        load_dotenv(env_file)
        logger.info(f"Loaded environment from: {env_file}")

    # Log migration configuration
    logger.info("="*60)
    logger.info("MIGRATION CONFIGURATION")
    logger.info("="*60)
    logger.info(f"Environment: {args.env}")
    logger.info(f"Source: {args.source}")
    logger.info(f"Source Path: {get_source_sqlite_path(args)}")
    logger.info(f"Schema Only: {args.schema_only}")
    logger.info(f"Data Only: {args.data_only}")
    logger.info(f"Drop Existing: {args.drop_existing}")
    logger.info(f"Batch Size: {args.batch_size}")
    logger.info(f"Tables: {args.tables or 'All'}")
    logger.info("="*60)

    try:
        # Test MySQL connection
        if not test_mysql_connection():
            logger.error("Cannot proceed without MySQL connection")
            return False

        source_path = get_source_sqlite_path(args)

        # Check if source database exists
        if not os.path.exists(source_path):
            logger.error(f"Source database not found: {source_path}")
            return False

        logger.info(f"Source database found: {source_path}")

        # Step 1: Schema Migration
        if not args.data_only:
            logger.info("\n" + "="*60)
            logger.info("STEP 1: SCHEMA MIGRATION")
            logger.info("="*60)

            schema_migrator = SchemaMigrator(source_sqlite_path=source_path)

            if not schema_migrator.migrate_schema(drop_existing=args.drop_existing):
                logger.error("Schema migration failed!")
                return False

            # Verify schema migration
            schema_verification = schema_migrator.verify_schema_migration()
            if not schema_verification['success']:
                logger.error("Schema verification failed!")
                logger.error(f"Missing tables: {schema_verification['missing_tables']}")
                return False

            logger.info("✓ Schema migration completed successfully")

        # Step 2: Data Migration
        if not args.schema_only:
            logger.info("\n" + "="*60)
            logger.info("STEP 2: DATA MIGRATION")
            logger.info("="*60)

            data_migrator = DataMigrator(
                source_sqlite_path=source_path,
                batch_size=args.batch_size
            )

            migration_result = data_migrator.migrate_all_data(tables=args.tables)

            if not migration_result['success']:
                logger.error("Data migration failed!")
                # Continue to verification even if some tables failed

            # Step 3: Verification
            if not args.skip_verification:
                logger.info("\n" + "="*60)
                logger.info("STEP 3: MIGRATION VERIFICATION")
                logger.info("="*60)

                verification_result = data_migrator.verify_migration()

                # Create migration report
                report_path = data_migrator.create_migration_report(
                    migration_result,
                    verification_result
                )

                logger.info(f"Migration report saved to: {report_path}")

                if not verification_result['success']:
                    logger.warning("Migration completed with discrepancies")
                    return False

        logger.info("\n" + "="*60)
        logger.info("✓ MIGRATION COMPLETED SUCCESSFULLY")
        logger.info("="*60)

        # Show connection info for application configuration
        config = get_database_config()
        logger.info("\nApplication configuration:")
        logger.info(f"USE_MYSQL=true")
        logger.info(f"DB_HOST={config.host}")
        logger.info(f"DB_PORT={config.port}")
        logger.info(f"DB_NAME={config.database}")
        logger.info(f"DB_USER={config.username}")

        return True

    except Exception as e:
        logger.error(f"Migration failed with error: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
