#!/usr/bin/env python3
"""
Migration script to sync cycling/readiness tables from production to development database.

Tables migrated:
- cycling_workouts
- readiness_entries
- sleep_summaries
- cardio_daily_metrics
- body_weights
- training_recommendations

Usage:
    python migrations/sync_prod_to_dev.py
"""
import os
import sys
import logging
import mysql.connector
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database configuration
DB_HOST = os.environ.get('DO_DB_HOST', 'db-mysql-fra1-07479-do-user-23762110-0.e.db.ondigitalocean.com')
DB_PORT = int(os.environ.get('DO_DB_PORT', 25060))
DB_USER = os.environ.get('DO_DB_USER', 'nutrition_user')
DB_PASSWORD = os.environ.get('DO_DB_PASS') or os.environ.get('DO_DB_PASSWORD')

PROD_DB = 'nutri_tracker_prod'
DEV_DB = 'nutri_tracker_dev'

# Tables to migrate (in order to handle foreign key dependencies)
TABLES_TO_MIGRATE = [
    'cycling_workouts',
    'readiness_entries',
    'sleep_summaries',
    'cardio_daily_metrics',
    'body_weights',
    'training_recommendations',
]


def get_connection(database: str):
    """Create a database connection."""
    if not DB_PASSWORD:
        raise ValueError("DO_DB_PASSWORD environment variable not set. Please set it before running.")
    
    # SSL configuration - DigitalOcean requires SSL
    ssl_config = {
        'ssl_verify_cert': False,  # Trust DO managed database
        'ssl_verify_identity': False,
    }
    
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=database,
        autocommit=False,
        **ssl_config
    )


def get_table_columns(cursor, table_name: str) -> list:
    """Get column names for a table."""
    cursor.execute(f"DESCRIBE {table_name}")
    return [row[0] for row in cursor.fetchall()]


def count_rows(cursor, table_name: str) -> int:
    """Count rows in a table."""
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    return cursor.fetchone()[0]


def migrate_table(prod_conn, dev_conn, table_name: str) -> dict:
    """
    Migrate a single table from production to development.
    
    Returns a dict with migration stats.
    """
    prod_cursor = prod_conn.cursor(dictionary=True)
    dev_cursor = dev_conn.cursor(dictionary=True)
    
    stats = {
        'table': table_name,
        'prod_rows': 0,
        'migrated': 0,
        'skipped': 0,
        'errors': []
    }
    
    try:
        # Check if table exists in production
        prod_cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
        if not prod_cursor.fetchone():
            logger.warning(f"Table '{table_name}' does not exist in production, skipping")
            return stats
        
        # Check if table exists in development
        dev_cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
        if not dev_cursor.fetchone():
            logger.warning(f"Table '{table_name}' does not exist in development, skipping")
            return stats
        
        # Get column names from production table
        prod_cursor.execute(f"DESCRIBE {table_name}")
        columns = [row['Field'] for row in prod_cursor.fetchall()]
        columns_str = ', '.join(f'`{c}`' for c in columns)
        placeholders = ', '.join(['%s'] * len(columns))
        
        # Count production rows
        prod_cursor.execute(f"SELECT COUNT(*) as cnt FROM {table_name}")
        stats['prod_rows'] = prod_cursor.fetchone()['cnt']
        logger.info(f"Table '{table_name}': {stats['prod_rows']} rows in production")
        
        if stats['prod_rows'] == 0:
            logger.info(f"No data to migrate for '{table_name}'")
            return stats
        
        # Clear development table
        logger.info(f"Clearing '{table_name}' in development...")
        dev_cursor.execute(f"DELETE FROM {table_name}")
        
        # Fetch all data from production
        prod_cursor.execute(f"SELECT {columns_str} FROM {table_name}")
        rows = prod_cursor.fetchall()
        
        # Insert into development using a new cursor without dictionary mode
        insert_cursor = dev_conn.cursor()
        insert_sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
        
        for row in rows:
            try:
                values = [row[col] for col in columns]
                insert_cursor.execute(insert_sql, values)
                stats['migrated'] += 1
            except Exception as e:
                stats['errors'].append(str(e))
                stats['skipped'] += 1
                logger.error(f"Error inserting row into '{table_name}': {e}")
        
        dev_conn.commit()
        logger.info(f"✓ Migrated {stats['migrated']} rows to '{table_name}'")
        
    except Exception as e:
        import traceback
        logger.error(f"Error migrating table '{table_name}': {e}")
        logger.error(traceback.format_exc())
        stats['errors'].append(str(e))
        dev_conn.rollback()
    
    return stats


def run_migration():
    """Run the full migration from production to development."""
    logger.info("=" * 60)
    logger.info("Production to Development Database Migration")
    logger.info("=" * 60)
    logger.info(f"Source: {PROD_DB}")
    logger.info(f"Target: {DEV_DB}")
    logger.info(f"Tables: {', '.join(TABLES_TO_MIGRATE)}")
    logger.info("=" * 60)
    
    prod_conn = None
    dev_conn = None
    all_stats = []
    
    try:
        # Connect to both databases
        logger.info("Connecting to production database...")
        prod_conn = get_connection(PROD_DB)
        logger.info("✓ Connected to production")
        
        logger.info("Connecting to development database...")
        dev_conn = get_connection(DEV_DB)
        logger.info("✓ Connected to development")
        
        # Migrate each table
        for table_name in TABLES_TO_MIGRATE:
            logger.info(f"\n--- Migrating: {table_name} ---")
            stats = migrate_table(prod_conn, dev_conn, table_name)
            all_stats.append(stats)
        
        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("MIGRATION SUMMARY")
        logger.info("=" * 60)
        
        total_migrated = 0
        total_skipped = 0
        
        for stats in all_stats:
            status = "✓" if not stats['errors'] else "⚠"
            logger.info(f"{status} {stats['table']}: {stats['migrated']} migrated, {stats['skipped']} skipped")
            total_migrated += stats['migrated']
            total_skipped += stats['skipped']
            
            if stats['errors']:
                for err in stats['errors'][:3]:
                    logger.info(f"    Error: {err[:80]}...")
        
        logger.info("-" * 60)
        logger.info(f"TOTAL: {total_migrated} records migrated, {total_skipped} skipped")
        logger.info("=" * 60)
        
        return total_skipped == 0
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if prod_conn:
            prod_conn.close()
        if dev_conn:
            dev_conn.close()


if __name__ == "__main__":
    # Check for password
    if not os.environ.get('DO_DB_PASS') and not os.environ.get('DO_DB_PASSWORD'):
        print("\n⚠️  DO_DB_PASS environment variable not set!")
        print("\nUsage:")
        print("  source .env  # or export DO_DB_PASS='your_password'")
        print("  python migrations/sync_prod_to_dev.py")
        sys.exit(1)
    
    success = run_migration()
    
    if success:
        print("\n✅ Migration completed successfully!")
    else:
        print("\n❌ Migration completed with errors!")
        sys.exit(1)

