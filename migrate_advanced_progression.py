"""
Migration script for advanced progressive overload tracking
Adds set-specific progression, pyramid pattern detection, and volume tracking
"""

import sqlite3
import os

def migrate():
    """Run the migration"""
    db_path = os.getenv('DATABASE_PATH', 'database.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Add columns to workout_sets for better tracking
        print("Adding columns to workout_sets...")
        cursor.execute('''
            ALTER TABLE workout_sets ADD COLUMN target_reps INTEGER
        ''')
        cursor.execute('''
            ALTER TABLE workout_sets ADD COLUMN progression_ready BOOLEAN DEFAULT 0
        ''')
        cursor.execute('''
            ALTER TABLE workout_sets ADD COLUMN last_progression_date DATE
        ''')
        print("✓ Updated workout_sets table")

    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("✓ workout_sets columns already exist")
        else:
            raise e

    # Create set-specific progression history table
    print("Creating set_progression_history table...")
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
            progression_type TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (exercise_id) REFERENCES exercises(id)
        )
    ''')
    print("✓ Created set_progression_history table")

    # Create exercise progression patterns table
    print("Creating exercise_progression_patterns table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exercise_progression_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            exercise_id INTEGER NOT NULL,
            pattern_type TEXT,
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

    # Create set-specific pattern ratios table for flexible set counts
    print("Creating set_pattern_ratios table...")
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

    # Create volume tracking table
    print("Creating workout_volume_tracking table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workout_volume_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_id INTEGER NOT NULL,
            exercise_id INTEGER NOT NULL,
            total_volume REAL,
            total_reps INTEGER,
            total_sets INTEGER,
            avg_intensity REAL,
            max_weight REAL,
            tonnage REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (workout_id) REFERENCES workout_sessions(id),
            FOREIGN KEY (exercise_id) REFERENCES exercises(id),
            UNIQUE(workout_id, exercise_id)
        )
    ''')
    print("✓ Created workout_volume_tracking table")

    # Create indexes for better performance
    print("Creating indexes...")
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_set_progression_user_exercise
        ON set_progression_history(user_id, exercise_id, set_number)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_volume_tracking_exercise
        ON workout_volume_tracking(exercise_id, workout_id)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_progression_patterns_user
        ON exercise_progression_patterns(user_id, exercise_id)
    ''')
    print("✓ Created indexes")

    # Update user_gym_preferences to include progression priorities
    try:
        print("Adding progression priorities to user_gym_preferences...")
        cursor.execute('''
            ALTER TABLE user_gym_preferences ADD COLUMN progression_priority_1 TEXT DEFAULT 'reps'
        ''')
        cursor.execute('''
            ALTER TABLE user_gym_preferences ADD COLUMN progression_priority_2 TEXT DEFAULT 'weight'
        ''')
        cursor.execute('''
            ALTER TABLE user_gym_preferences ADD COLUMN progression_priority_3 TEXT DEFAULT 'volume'
        ''')
        cursor.execute('''
            ALTER TABLE user_gym_preferences ADD COLUMN progression_priority_4 TEXT DEFAULT 'sets'
        ''')
        cursor.execute('''
            ALTER TABLE user_gym_preferences ADD COLUMN progression_priority_5 TEXT DEFAULT 'exercises'
        ''')
        cursor.execute('''
            ALTER TABLE user_gym_preferences ADD COLUMN pyramid_preference TEXT DEFAULT 'auto_detect'
        ''')
        print("✓ Updated user_gym_preferences table")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("✓ user_gym_preferences columns already exist")
        else:
            raise e

    # Add sample progression data for testing (user_id=2)
    print("Adding sample progression data...")

    # Check if user preferences exist
    cursor.execute('SELECT user_id FROM user_gym_preferences WHERE user_id = 2')
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO user_gym_preferences (
                user_id, progression_strategy, min_reps_target, max_reps_target,
                weight_increment_upper, weight_increment_lower,
                progression_priority_1, progression_priority_2, progression_priority_3,
                progression_priority_4, progression_priority_5, pyramid_preference
            ) VALUES (2, 'reps_first', 10, 15, 2.5, 5.0,
                     'reps', 'weight', 'volume', 'sets', 'exercises', 'auto_detect')
        ''')
        print("✓ Added default preferences for user 2")

    conn.commit()
    print("\n✓ Migration completed successfully!")

    # Show summary
    cursor.execute('''
        SELECT COUNT(*) FROM sqlite_master
        WHERE type='table' AND name IN (
            'set_progression_history',
            'exercise_progression_patterns',
            'workout_volume_tracking'
        )
    ''')
    table_count = cursor.fetchone()[0]
    print(f"Total new tables created: {table_count}")

    conn.close()

if __name__ == '__main__':
    migrate()
