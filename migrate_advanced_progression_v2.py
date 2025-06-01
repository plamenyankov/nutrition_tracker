#!/usr/bin/env python3
"""
Migration script for Advanced Progressive Overload V2 features
Adds tables and columns for set-specific progression tracking
"""

import sqlite3
import os

def migrate():
    # Get database path from environment or use default
    db_path = os.getenv('DATABASE_PATH', 'database.db')

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 1. Update workout_sets table
        print("Updating workout_sets table...")
        cursor.execute("PRAGMA table_info(workout_sets)")
        columns = [col[1] for col in cursor.fetchall()]

        workout_sets_additions = [
            ('target_reps', 'INTEGER'),
            ('progression_ready', 'BOOLEAN DEFAULT 0'),
            ('last_progression_date', 'DATE')
        ]

        for column_name, column_def in workout_sets_additions:
            if column_name not in columns:
                cursor.execute(f'''
                    ALTER TABLE workout_sets
                    ADD COLUMN {column_name} {column_def}
                ''')
                print(f"✓ Added {column_name} to workout_sets")

        # 2. Create set_progression_history table
        print("\nCreating set_progression_history table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS set_progression_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                exercise_id INTEGER NOT NULL,
                set_number INTEGER NOT NULL,
                progression_date DATE NOT NULL,
                old_weight REAL,
                new_weight REAL,
                old_reps INTEGER,
                new_reps INTEGER,
                progression_type TEXT, -- 'weight', 'reps', 'added_set'
                notes TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (exercise_id) REFERENCES exercises(id)
            )
        ''')
        print("✓ Created set_progression_history table")

        # 3. Create exercise_progression_patterns table
        print("\nCreating exercise_progression_patterns table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS exercise_progression_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                exercise_id INTEGER NOT NULL,
                pattern_type TEXT, -- 'ascending', 'descending', 'straight', 'double_pyramid'
                typical_sets INTEGER DEFAULT 3,
                detected_pattern TEXT,
                confidence_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (exercise_id) REFERENCES exercises(id),
                UNIQUE(user_id, exercise_id)
            )
        ''')
        print("✓ Created exercise_progression_patterns table")

        # 4. Create set_pattern_ratios table
        print("\nCreating set_pattern_ratios table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS set_pattern_ratios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_id INTEGER NOT NULL,
                set_number INTEGER NOT NULL,
                weight_ratio REAL DEFAULT 1.0,
                typical_reps INTEGER,
                notes TEXT,
                FOREIGN KEY (pattern_id) REFERENCES exercise_progression_patterns(id) ON DELETE CASCADE,
                UNIQUE(pattern_id, set_number)
            )
        ''')
        print("✓ Created set_pattern_ratios table")

        # 5. Create workout_volume_tracking table
        print("\nCreating workout_volume_tracking table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workout_volume_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workout_id INTEGER NOT NULL,
                exercise_id INTEGER NOT NULL,
                total_volume REAL,
                total_reps INTEGER,
                total_sets INTEGER,
                avg_intensity REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (workout_id) REFERENCES workout_sessions(id),
                FOREIGN KEY (exercise_id) REFERENCES exercises(id),
                UNIQUE(workout_id, exercise_id)
            )
        ''')
        print("✓ Created workout_volume_tracking table")

        # Create indexes for better performance
        print("\nCreating indexes...")
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_set_progression_user_exercise
            ON set_progression_history(user_id, exercise_id, set_number)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_volume_tracking_workout
            ON workout_volume_tracking(workout_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_progression_patterns_user
            ON exercise_progression_patterns(user_id, exercise_id)
        ''')
        print("✓ Created indexes")

        conn.commit()
        print("\n✓ Advanced Progression V2 migration completed successfully!")

    except sqlite3.Error as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

    return True

if __name__ == '__main__':
    if migrate():
        print("\nDatabase is ready for advanced progression features!")
    else:
        print("\nMigration failed. Please check the error messages above.")
