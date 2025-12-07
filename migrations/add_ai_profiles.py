"""
Migration: Add ai_profiles table

Stores AI prompt configurations for Coach and Analyzer.
Allows versioning and A/B testing of different prompt strategies.

Run: python migrations/add_ai_profiles.py
"""
import os
import sys
import json
import logging

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from models.database.connection_manager import get_db_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Create the ai_profiles table"""
    try:
        db_manager = get_db_manager()
        logger.info("Starting migration: Add ai_profiles table")

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Check if table already exists
            cursor.execute("""
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'ai_profiles'
            """)
            exists = cursor.fetchone()[0] > 0

            if exists:
                logger.info("Table 'ai_profiles' already exists, skipping creation")
                return True

            # Create the table
            # Using TEXT for prompts and settings_json for maximum compatibility
            cursor.execute("""
                CREATE TABLE ai_profiles (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(50) NOT NULL,
                    version VARCHAR(50) NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT FALSE,
                    system_prompt TEXT NOT NULL,
                    user_prompt_template TEXT,
                    settings_json TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    
                    UNIQUE KEY unique_name_version (name, version),
                    INDEX idx_name_active (name, is_active)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            conn.commit()
            logger.info("✓ Created ai_profiles table")

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
                AND TABLE_NAME = 'ai_profiles'
                ORDER BY ORDINAL_POSITION
            """)
            columns = cursor.fetchall()
            
            logger.info("ai_profiles columns:")
            for col in columns:
                logger.info(f"  {col[0]}: {col[1]} (nullable: {col[2]})")
            
            # Check indexes
            cursor.execute("""
                SHOW INDEX FROM ai_profiles
            """)
            indexes = cursor.fetchall()
            logger.info(f"Indexes: {len(indexes)} found")

        return True

    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("AI Profiles Table Migration")
    print("=" * 50)
    print("\nThis migration will create the ai_profiles table")
    print("with columns: id, name, version, is_active,")
    print("system_prompt, user_prompt_template, settings_json,")
    print("created_at, updated_at")
    print("")

    if run_migration():
        print("\nVerifying schema changes...")
        verify_schema()
    else:
        print("Migration failed!")
        sys.exit(1)

