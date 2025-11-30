"""
Migration: Add training_recommendations table

Stores AI-generated training recommendations per user per date.

Run: python migrations/add_training_recommendations.py
"""
import os
import sys
import logging

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from models.database.connection_manager import get_db_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Create the training_recommendations table"""
    try:
        db_manager = get_db_manager()
        logger.info("Starting migration: Add training_recommendations table")

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Check if table already exists
            cursor.execute("""
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'training_recommendations'
            """)
            exists = cursor.fetchone()[0] > 0

            if exists:
                logger.info("Table 'training_recommendations' already exists, skipping creation")
                return True

            # Create the table
            cursor.execute("""
                CREATE TABLE training_recommendations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id VARCHAR(100) NOT NULL,
                    date DATE NOT NULL,
                    day_type VARCHAR(50) NOT NULL,
                    duration_minutes INT,
                    payload_json JSON NOT NULL,
                    model_name VARCHAR(50),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    
                    UNIQUE KEY unique_user_date (user_id, date),
                    INDEX idx_user_id (user_id),
                    INDEX idx_date (date)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            conn.commit()
            logger.info("✓ Created training_recommendations table")

        logger.info("Migration completed successfully!")
        return True

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_schema():
    """Verify the table was created correctly"""
    try:
        db_manager = get_db_manager()
        
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check columns
            cursor.execute("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'training_recommendations'
                ORDER BY ORDINAL_POSITION
            """)
            columns = cursor.fetchall()
            
            logger.info("training_recommendations columns:")
            for col in columns:
                logger.info(f"  {col[0]}: {col[1]} (nullable: {col[2]})")
            
            # Check indexes
            cursor.execute("""
                SHOW INDEX FROM training_recommendations
            """)
            indexes = cursor.fetchall()
            logger.info(f"Indexes: {len(indexes)} found")

        return True

    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("Training Recommendations Table Migration")
    print("=" * 50)
    print("\nThis migration will create the training_recommendations table")
    print("with columns: id, user_id, date, day_type, duration_minutes,")
    print("payload_json, model_name, created_at, updated_at")
    print("")

    if run_migration():
        print("\nVerifying schema changes...")
        verify_schema()
    else:
        print("Migration failed!")
        sys.exit(1)

