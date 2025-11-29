"""
Migration script to add CyclingWorkout and ReadinessEntry tables.
Run this script to add the new tables for the Cycling & Readiness feature.
"""
import os
import sys
import logging

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from models.database.connection_manager import get_db_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_cycling_workout_table():
    """Create the cycling_workouts table"""
    return """
    CREATE TABLE IF NOT EXISTS cycling_workouts (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id VARCHAR(100),
        date DATE NOT NULL,
        start_time TIME,
        source VARCHAR(50) DEFAULT 'indoor_cycle',
        notes TEXT,
        duration_sec INT,
        distance_km FLOAT,
        avg_heart_rate INT,
        max_heart_rate INT,
        avg_power_w FLOAT,
        max_power_w FLOAT,
        normalized_power_w FLOAT,
        intensity_factor FLOAT,
        tss FLOAT,
        avg_cadence INT,
        kcal_active INT,
        kcal_total INT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_cycling_user_date (user_id, date),
        INDEX idx_cycling_date (date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """


def create_readiness_entry_table():
    """Create the readiness_entries table"""
    return """
    CREATE TABLE IF NOT EXISTS readiness_entries (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id VARCHAR(100),
        date DATE NOT NULL,
        -- Morning inputs
        energy INT CHECK (energy BETWEEN 1 AND 5),
        mood INT CHECK (mood BETWEEN 1 AND 3),
        muscle_fatigue INT CHECK (muscle_fatigue BETWEEN 1 AND 3),
        hrv_status INT CHECK (hrv_status BETWEEN -1 AND 1),
        rhr_status INT CHECK (rhr_status BETWEEN -1 AND 1),
        min_hr_status INT CHECK (min_hr_status BETWEEN -1 AND 1),
        sleep_minutes INT,
        deep_sleep_minutes INT,
        wakeups_count INT,
        stress_level INT CHECK (stress_level BETWEEN 1 AND 3),
        symptoms_flag BOOLEAN DEFAULT FALSE,
        morning_score INT CHECK (morning_score BETWEEN 0 AND 100),
        -- Evening fields
        evening_note TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY unique_user_date (user_id, date),
        INDEX idx_readiness_user_date (user_id, date),
        INDEX idx_readiness_date (date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """


def create_sleep_summary_table():
    """Create the sleep_summaries table for storing extracted sleep data"""
    return """
    CREATE TABLE IF NOT EXISTS sleep_summaries (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id VARCHAR(100),
        date DATE NOT NULL,
        sleep_start_time TIME,
        sleep_end_time TIME,
        total_sleep_minutes INT,
        deep_sleep_minutes INT,
        wakeups_count INT,
        min_heart_rate INT,
        avg_heart_rate INT,
        max_heart_rate INT,
        notes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_sleep_user_date (user_id, date),
        INDEX idx_sleep_date (date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """


def run_migration():
    """Execute the migration to create new tables"""
    try:
        db_manager = get_db_manager()
        logger.info("Starting migration: Creating Cycling & Readiness tables")

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Create cycling_workouts table
            logger.info("Creating cycling_workouts table...")
            cursor.execute(create_cycling_workout_table())
            logger.info("✓ cycling_workouts table created")

            # Create readiness_entries table
            logger.info("Creating readiness_entries table...")
            cursor.execute(create_readiness_entry_table())
            logger.info("✓ readiness_entries table created")

            # Create sleep_summaries table
            logger.info("Creating sleep_summaries table...")
            cursor.execute(create_sleep_summary_table())
            logger.info("✓ sleep_summaries table created")

            conn.commit()

        logger.info("Migration completed successfully!")
        return True

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


def verify_tables():
    """Verify that the tables were created"""
    try:
        db_manager = get_db_manager()

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            tables = ['cycling_workouts', 'readiness_entries', 'sleep_summaries']
            for table in tables:
                cursor.execute(f"SHOW TABLES LIKE '{table}'")
                result = cursor.fetchone()
                if result:
                    logger.info(f"✓ Table {table} exists")
                else:
                    logger.warning(f"✗ Table {table} not found")

        return True

    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("Cycling & Readiness Tables Migration")
    print("=" * 50)

    if run_migration():
        print("\nVerifying tables...")
        verify_tables()
    else:
        print("Migration failed!")
        sys.exit(1)

