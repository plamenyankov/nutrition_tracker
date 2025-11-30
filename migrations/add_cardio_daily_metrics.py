"""
Migration: Add cardio_daily_metrics table for Apple Health RHR and HRV data
Run: python migrations/add_cardio_daily_metrics.py
"""
import os
import sys
import logging

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from models.database.connection_manager import get_db_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_cardio_daily_metrics_table():
    """Create the cardio_daily_metrics table"""
    return """
    CREATE TABLE IF NOT EXISTS cardio_daily_metrics (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id VARCHAR(100),
        date DATE NOT NULL,
        rhr_low_bpm INT,
        rhr_high_bpm INT,
        hrv_low_ms INT,
        hrv_high_ms INT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY unique_user_date (user_id, date),
        INDEX idx_cardio_user_date (user_id, date),
        INDEX idx_cardio_date (date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """


def run_migration():
    """Execute the migration"""
    try:
        db_manager = get_db_manager()
        logger.info("Starting migration: Creating cardio_daily_metrics table")

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            logger.info("Creating cardio_daily_metrics table...")
            cursor.execute(create_cardio_daily_metrics_table())
            logger.info("✓ cardio_daily_metrics table created")

            conn.commit()

        logger.info("Migration completed successfully!")
        return True

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_table():
    """Verify that the table was created"""
    try:
        db_manager = get_db_manager()

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SHOW TABLES LIKE 'cardio_daily_metrics'")
            result = cursor.fetchone()
            if result:
                logger.info("✓ Table cardio_daily_metrics exists")
            else:
                logger.warning("✗ Table cardio_daily_metrics not found")

        return True

    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("Cardio Daily Metrics Table Migration")
    print("=" * 50)

    if run_migration():
        print("\nVerifying table...")
        verify_table()
    else:
        print("Migration failed!")
        sys.exit(1)

