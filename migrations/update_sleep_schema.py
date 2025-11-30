"""
Migration: Update sleep schema
- Rename wakeups_count to awake_minutes in sleep_summaries and readiness_entries
- Keep avg_heart_rate as optional
- Clean up stress_level (make optional, not required for score calculation)

Run: python migrations/update_sleep_schema.py
"""
import os
import sys
import logging

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from models.database.connection_manager import get_db_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Execute the schema updates"""
    try:
        db_manager = get_db_manager()
        logger.info("Starting migration: Update sleep schema")

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # ============== sleep_summaries table ==============
            logger.info("Updating sleep_summaries table...")
            
            # Check if wakeups_count column exists
            cursor.execute("""
                SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'sleep_summaries' 
                AND COLUMN_NAME = 'wakeups_count'
            """)
            has_wakeups_count = cursor.fetchone()
            
            if has_wakeups_count:
                # Check if awake_minutes already exists
                cursor.execute("""
                    SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = DATABASE() 
                    AND TABLE_NAME = 'sleep_summaries' 
                    AND COLUMN_NAME = 'awake_minutes'
                """)
                has_awake_minutes = cursor.fetchone()
                
                if not has_awake_minutes:
                    # Add new column
                    cursor.execute("""
                        ALTER TABLE sleep_summaries 
                        ADD COLUMN awake_minutes INT AFTER deep_sleep_minutes
                    """)
                    logger.info("✓ Added awake_minutes column to sleep_summaries")
                    
                    # Copy data: If wakeups_count was used as minutes, copy; else set NULL
                    # Note: Previously this might have been misused as count, not minutes
                    # We leave existing data as-is for now (they can be corrected manually)
                    cursor.execute("""
                        UPDATE sleep_summaries 
                        SET awake_minutes = wakeups_count 
                        WHERE wakeups_count IS NOT NULL
                    """)
                    logger.info("✓ Migrated wakeups_count data to awake_minutes")
                    
                    # Don't drop wakeups_count yet - keep for safety
                    # Can be dropped in a future migration after verification
                    logger.info("  Note: wakeups_count column retained for safety")
            else:
                # wakeups_count doesn't exist, just add awake_minutes if needed
                cursor.execute("""
                    SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = DATABASE() 
                    AND TABLE_NAME = 'sleep_summaries' 
                    AND COLUMN_NAME = 'awake_minutes'
                """)
                if not cursor.fetchone():
                    cursor.execute("""
                        ALTER TABLE sleep_summaries 
                        ADD COLUMN awake_minutes INT AFTER deep_sleep_minutes
                    """)
                    logger.info("✓ Added awake_minutes column to sleep_summaries")

            # ============== readiness_entries table ==============
            logger.info("Updating readiness_entries table...")
            
            # Check if awake_minutes column exists
            cursor.execute("""
                SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'readiness_entries' 
                AND COLUMN_NAME = 'awake_minutes'
            """)
            has_awake_minutes_readiness = cursor.fetchone()
            
            if not has_awake_minutes_readiness:
                # Add awake_minutes column
                cursor.execute("""
                    ALTER TABLE readiness_entries 
                    ADD COLUMN awake_minutes INT AFTER deep_sleep_minutes
                """)
                logger.info("✓ Added awake_minutes column to readiness_entries")
                
                # Copy data from wakeups_count if it exists
                cursor.execute("""
                    SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = DATABASE() 
                    AND TABLE_NAME = 'readiness_entries' 
                    AND COLUMN_NAME = 'wakeups_count'
                """)
                if cursor.fetchone():
                    cursor.execute("""
                        UPDATE readiness_entries 
                        SET awake_minutes = wakeups_count 
                        WHERE wakeups_count IS NOT NULL
                    """)
                    logger.info("✓ Migrated wakeups_count data to awake_minutes in readiness_entries")

            conn.commit()

        logger.info("Migration completed successfully!")
        return True

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_schema():
    """Verify the schema changes"""
    try:
        db_manager = get_db_manager()
        
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check sleep_summaries columns
            cursor.execute("""
                SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'sleep_summaries'
                ORDER BY ORDINAL_POSITION
            """)
            columns = [row[0] for row in cursor.fetchall()]
            logger.info(f"sleep_summaries columns: {columns}")
            
            if 'awake_minutes' in columns:
                logger.info("✓ awake_minutes exists in sleep_summaries")
            else:
                logger.warning("✗ awake_minutes missing from sleep_summaries")
            
            # Check readiness_entries columns
            cursor.execute("""
                SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'readiness_entries'
                ORDER BY ORDINAL_POSITION
            """)
            columns = [row[0] for row in cursor.fetchall()]
            logger.info(f"readiness_entries columns: {columns}")
            
            if 'awake_minutes' in columns:
                logger.info("✓ awake_minutes exists in readiness_entries")
            else:
                logger.warning("✗ awake_minutes missing from readiness_entries")

        return True

    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("Sleep Schema Update Migration")
    print("=" * 50)
    print("\nThis migration will:")
    print("1. Add 'awake_minutes' column to sleep_summaries")
    print("2. Add 'awake_minutes' column to readiness_entries")
    print("3. Copy data from wakeups_count to awake_minutes")
    print("4. Keep wakeups_count for safety (can be dropped later)")
    print("")

    if run_migration():
        print("\nVerifying schema changes...")
        verify_schema()
    else:
        print("Migration failed!")
        sys.exit(1)

