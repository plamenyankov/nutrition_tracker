"""
Migration: Add manual override flags to cardio_daily_metrics table

This allows tracking whether RHR/HRV values were entered manually
or imported from Apple Health screenshots.

Run: python migrations/add_cardio_manual_override.py
"""
import os
import sys
import logging

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from models.database.connection_manager import get_db_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Execute the migration to add manual override flags"""
    try:
        db_manager = get_db_manager()
        logger.info("Starting migration: Adding manual override flags to cardio_daily_metrics")

        with db_manager.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)

            # Check if the table exists
            cursor.execute("SHOW TABLES LIKE 'cardio_daily_metrics'")
            if not cursor.fetchone():
                logger.error("Table cardio_daily_metrics does not exist. Run add_cardio_daily_metrics.py first.")
                return False

            # Check if rhr_manual_override column already exists
            cursor.execute("SHOW COLUMNS FROM cardio_daily_metrics LIKE 'rhr_manual_override'")
            if cursor.fetchone():
                logger.info("Column rhr_manual_override already exists. Migration already applied.")
                return True

            # Add the new columns
            logger.info("Adding rhr_manual_override column...")
            cursor.execute("""
                ALTER TABLE cardio_daily_metrics 
                ADD COLUMN rhr_manual_override BOOLEAN DEFAULT FALSE AFTER rhr_bpm
            """)

            logger.info("Adding hrv_manual_override column...")
            cursor.execute("""
                ALTER TABLE cardio_daily_metrics 
                ADD COLUMN hrv_manual_override BOOLEAN DEFAULT FALSE AFTER hrv_high_ms
            """)

            conn.commit()
            logger.info("✓ Migration completed successfully")

        return True

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_schema():
    """Verify the table schema after migration"""
    try:
        db_manager = get_db_manager()

        with db_manager.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)

            cursor.execute("DESCRIBE cardio_daily_metrics")
            columns = {row['Field']: row for row in cursor.fetchall()}

            expected = ['rhr_manual_override', 'hrv_manual_override']
            
            logger.info("Checking for new columns:")
            for col in expected:
                if col in columns:
                    logger.info(f"  ✓ {col}: {columns[col]['Type']}")
                else:
                    logger.warning(f"  ✗ {col}: NOT FOUND")

        return True

    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Add Cardio Manual Override Flags Migration")
    print("=" * 60)
    print("\nThis migration will:")
    print("  - Add rhr_manual_override (BOOLEAN) column")
    print("  - Add hrv_manual_override (BOOLEAN) column")
    print()

    if run_migration():
        print("\nVerifying schema...")
        verify_schema()
    else:
        print("Migration failed!")
        sys.exit(1)

