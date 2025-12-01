"""
Migration: Add ai_workout_analyses table

Stores AI-generated workout analysis per user per workout.

Run: python migrations/add_ai_workout_analyses.py
"""
import os
import sys
import logging

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from models.database.connection_manager import get_db_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Create the ai_workout_analyses table"""
    try:
        db_manager = get_db_manager()
        logger.info("Starting migration: Add ai_workout_analyses table")

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Check if table already exists
            cursor.execute("""
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'ai_workout_analyses'
            """)
            exists = cursor.fetchone()[0] > 0

            if exists:
                logger.info("Table 'ai_workout_analyses' already exists, skipping creation")
                return True

            # Create the table
            cursor.execute("""
                CREATE TABLE ai_workout_analyses (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id VARCHAR(100) NOT NULL,
                    workout_id INT NOT NULL,
                    date DATE NOT NULL,
                    
                    -- Scores (0-100)
                    overall_score INT,
                    compliance_score INT,
                    intensity_score INT,
                    duration_score INT,
                    hr_response_score INT,
                    
                    -- Labels
                    execution_label VARCHAR(50),
                    fatigue_risk VARCHAR(20),
                    
                    -- Notes
                    notes_short TEXT,
                    notes_detailed TEXT,
                    
                    -- Raw JSON from AI response
                    raw_json JSON,
                    
                    -- Model/prompt version for tracking
                    prompt_version VARCHAR(50),
                    
                    -- Timestamps
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    
                    -- Constraints
                    UNIQUE KEY unique_user_workout (user_id, workout_id),
                    INDEX idx_user_id (user_id),
                    INDEX idx_workout_id (workout_id),
                    INDEX idx_date (date),
                    INDEX idx_user_date (user_id, date),
                    
                    -- Foreign key to workouts (if cycling_workouts exists)
                    CONSTRAINT fk_analysis_workout 
                        FOREIGN KEY (workout_id) 
                        REFERENCES cycling_workouts(id) 
                        ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            conn.commit()
            logger.info("✓ Created ai_workout_analyses table")

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
                AND TABLE_NAME = 'ai_workout_analyses'
                ORDER BY ORDINAL_POSITION
            """)
            columns = cursor.fetchall()
            
            logger.info("ai_workout_analyses columns:")
            for col in columns:
                logger.info(f"  {col[0]}: {col[1]} (nullable: {col[2]})")
            
            # Check indexes
            cursor.execute("""
                SHOW INDEX FROM ai_workout_analyses
            """)
            indexes = cursor.fetchall()
            logger.info(f"Indexes: {len(indexes)} found")

        return True

    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("AI Workout Analyses Table Migration")
    print("=" * 50)
    print("\nThis migration will create the ai_workout_analyses table")
    print("with columns: id, user_id, workout_id, date, scores,")
    print("execution_label, fatigue_risk, notes, raw_json, etc.")
    print("")

    if run_migration():
        print("\nVerifying schema changes...")
        verify_schema()
    else:
        print("Migration failed!")
        sys.exit(1)

