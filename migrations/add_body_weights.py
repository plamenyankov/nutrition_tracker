"""
Migration: Add body_weights table for tracking weekly weight entries.

Used for accurate VO2 Index (W/kg) calculations in Analytics.

Run: python migrations/add_body_weights.py
"""
import os
import sys
import logging

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from models.database.connection_manager import get_db_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration() -> bool:
    """
    Create body_weights table for storing user weight entries.
    
    Schema:
    - id: Primary key
    - user_id: Foreign key to users
    - date: Date of weight entry (unique per user+date)
    - weight_kg: Body weight in kilograms
    - created_at: Timestamp of creation
    - updated_at: Timestamp of last update
    """
    try:
        db_manager = get_db_manager()
        logger.info("Starting migration: Adding body_weights table")
        
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if table already exists
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = 'body_weights'
            """)
            
            if cursor.fetchone()[0] > 0:
                logger.info("Table body_weights already exists. Migration already applied.")
                return True
            
            # Create the body_weights table
            cursor.execute("""
                CREATE TABLE body_weights (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL,
                    date DATE NOT NULL,
                    weight_kg FLOAT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_user_date (user_id, date),
                    INDEX idx_user_date (user_id, date)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            conn.commit()
            logger.info("✓ Created body_weights table successfully")
            return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


def rollback_migration() -> bool:
    """Drop the body_weights table."""
    try:
        db_manager = get_db_manager()
        logger.info("Rolling back: Dropping body_weights table")
        
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS body_weights")
            conn.commit()
            logger.info("✓ Dropped body_weights table")
            return True
    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        return False


if __name__ == "__main__":
    success = run_migration()
    if success:
        print("✅ Migration completed successfully!")
    else:
        print("❌ Migration failed!")
        sys.exit(1)
