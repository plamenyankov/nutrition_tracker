"""
Migration: Fix cardio_daily_metrics schema
- Replace rhr_low_bpm and rhr_high_bpm with single rhr_bpm (RHR is a single value per day)
- Keep hrv_low_ms and hrv_high_ms (HRV is a range)

Run: python migrations/fix_cardio_schema.py
"""
import os
import sys
import logging

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from models.database.connection_manager import get_db_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Execute the migration to fix cardio_daily_metrics schema"""
    try:
        db_manager = get_db_manager()
        logger.info("Starting migration: Fixing cardio_daily_metrics schema")

        with db_manager.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)

            # Check if the table exists
            cursor.execute("SHOW TABLES LIKE 'cardio_daily_metrics'")
            if not cursor.fetchone():
                logger.info("Table cardio_daily_metrics does not exist. Creating with correct schema...")
                cursor.execute("""
                    CREATE TABLE cardio_daily_metrics (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id VARCHAR(100),
                        date DATE NOT NULL,
                        rhr_bpm INT,
                        hrv_low_ms INT,
                        hrv_high_ms INT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        UNIQUE KEY unique_user_date (user_id, date),
                        INDEX idx_cardio_user_date (user_id, date),
                        INDEX idx_cardio_date (date)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                conn.commit()
                logger.info("✓ Table created with correct schema")
                return True

            # Check if rhr_bpm already exists (migration already ran)
            cursor.execute("SHOW COLUMNS FROM cardio_daily_metrics LIKE 'rhr_bpm'")
            if cursor.fetchone():
                logger.info("Column rhr_bpm already exists. Migration already applied.")
                return True

            # Check if old columns exist
            cursor.execute("SHOW COLUMNS FROM cardio_daily_metrics LIKE 'rhr_low_bpm'")
            has_old_columns = cursor.fetchone() is not None

            if has_old_columns:
                logger.info("Migrating from old schema (rhr_low_bpm/rhr_high_bpm) to new (rhr_bpm)...")

                # Step 1: Add the new rhr_bpm column
                logger.info("Adding rhr_bpm column...")
                cursor.execute("""
                    ALTER TABLE cardio_daily_metrics 
                    ADD COLUMN rhr_bpm INT AFTER date
                """)

                # Step 2: Migrate data from rhr_low_bpm to rhr_bpm
                logger.info("Migrating data from rhr_low_bpm to rhr_bpm...")
                cursor.execute("""
                    UPDATE cardio_daily_metrics 
                    SET rhr_bpm = rhr_low_bpm 
                    WHERE rhr_low_bpm IS NOT NULL
                """)
                affected = cursor.rowcount
                logger.info(f"✓ Migrated {affected} rows")

                # Step 3: Drop the old columns
                logger.info("Dropping old columns (rhr_low_bpm, rhr_high_bpm)...")
                cursor.execute("""
                    ALTER TABLE cardio_daily_metrics 
                    DROP COLUMN rhr_low_bpm,
                    DROP COLUMN rhr_high_bpm
                """)

                conn.commit()
                logger.info("✓ Schema migration completed successfully")
            else:
                # Table exists but has neither old nor new columns - add rhr_bpm
                logger.info("Adding rhr_bpm column to existing table...")
                cursor.execute("""
                    ALTER TABLE cardio_daily_metrics 
                    ADD COLUMN rhr_bpm INT AFTER date
                """)
                conn.commit()
                logger.info("✓ Column added")

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

            expected = ['id', 'user_id', 'date', 'rhr_bpm', 'hrv_low_ms', 'hrv_high_ms', 'created_at', 'updated_at']
            
            logger.info("Current schema:")
            for col in columns:
                logger.info(f"  - {col}: {columns[col]['Type']}")

            missing = [c for c in expected if c not in columns]
            if missing:
                logger.warning(f"Missing expected columns: {missing}")
            else:
                logger.info("✓ All expected columns present")

            # Check for old columns that should be removed
            old_cols = ['rhr_low_bpm', 'rhr_high_bpm']
            found_old = [c for c in old_cols if c in columns]
            if found_old:
                logger.warning(f"Old columns still present: {found_old}")
            else:
                logger.info("✓ Old columns removed")

            # Show current data count
            cursor.execute("SELECT COUNT(*) as cnt FROM cardio_daily_metrics")
            count = cursor.fetchone()['cnt']
            logger.info(f"Current row count: {count}")

            if count > 0:
                cursor.execute("""
                    SELECT date, rhr_bpm, hrv_low_ms, hrv_high_ms 
                    FROM cardio_daily_metrics 
                    ORDER BY date DESC 
                    LIMIT 5
                """)
                logger.info("Sample data:")
                for row in cursor.fetchall():
                    logger.info(f"  {row['date']}: RHR={row['rhr_bpm']}, HRV={row['hrv_low_ms']}-{row['hrv_high_ms']}")

        return True

    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Fix Cardio Daily Metrics Schema Migration")
    print("=" * 60)
    print("\nThis migration will:")
    print("  - Replace rhr_low_bpm/rhr_high_bpm with single rhr_bpm")
    print("  - Keep hrv_low_ms and hrv_high_ms unchanged")
    print()

    if run_migration():
        print("\nVerifying schema...")
        verify_schema()
    else:
        print("Migration failed!")
        sys.exit(1)

