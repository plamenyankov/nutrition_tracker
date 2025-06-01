#!/usr/bin/env python3
"""
Migration script to add progressive overload tracking features to the gym tracker.
This includes user preferences, exercise-specific rules, and progression history.
Modified to work without a users table (using hardcoded user_id).
"""

import sqlite3
import os
from datetime import datetime

def get_db_path():
    """Get the database path from environment or use default"""
    return os.getenv('DATABASE_PATH', 'database.db')

def migrate():
    """Run the migration to add progressive overload features"""
    db_path = get_db_path()
    print(f"Running progressive overload migration on database: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # First, clean up any existing tables from failed migration
        print("Cleaning up existing tables if any...")
        cursor.execute('DROP TABLE IF EXISTS progression_history')
        cursor.execute('DROP TABLE IF EXISTS exercise_progression_rules')
        cursor.execute('DROP TABLE IF EXISTS user_gym_preferences')

        # Create user_gym_preferences table (without foreign key to users)
        print("Creating user_gym_preferences table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_gym_preferences (
                user_id INTEGER PRIMARY KEY,
                progression_strategy TEXT DEFAULT 'reps_first',
                min_reps_target INTEGER DEFAULT 10,
                max_reps_target INTEGER DEFAULT 15,
                weight_increment_upper REAL DEFAULT 2.5,
                weight_increment_lower REAL DEFAULT 5.0,
                rest_timer_enabled BOOLEAN DEFAULT 1,
                progression_notification_enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create exercise_progression_rules table
        print("Creating exercise_progression_rules table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS exercise_progression_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                exercise_id INTEGER NOT NULL,
                custom_min_reps INTEGER,
                custom_max_reps INTEGER,
                custom_weight_increment REAL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (exercise_id) REFERENCES exercises(id),
                UNIQUE(user_id, exercise_id)
            )
        ''')

        # Create progression_history table
        print("Creating progression_history table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS progression_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                exercise_id INTEGER NOT NULL,
                progression_date DATE NOT NULL,
                old_weight REAL,
                new_weight REAL,
                old_reps_min INTEGER,
                old_reps_max INTEGER,
                new_reps_target INTEGER,
                progression_type TEXT, -- 'weight_increase', 'reps_increase', 'deload'
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (exercise_id) REFERENCES exercises(id)
            )
        ''')

        # Add new columns to workout_sets if they don't exist
        print("Adding new columns to workout_sets...")

        # Check if columns exist first
        cursor.execute("PRAGMA table_info(workout_sets)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'rpe' not in columns:
            cursor.execute('ALTER TABLE workout_sets ADD COLUMN rpe INTEGER')
            print("  - Added rpe column")
        else:
            print("  - rpe column already exists")

        if 'form_quality' not in columns:
            cursor.execute('ALTER TABLE workout_sets ADD COLUMN form_quality INTEGER')
            print("  - Added form_quality column")
        else:
            print("  - form_quality column already exists")

        if 'notes' not in columns:
            cursor.execute('ALTER TABLE workout_sets ADD COLUMN notes TEXT')
            print("  - Added notes column")
        else:
            print("  - notes column already exists")

        # Create indexes for better performance
        print("Creating indexes...")
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_progression_history_user_exercise
            ON progression_history(user_id, exercise_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_progression_history_date
            ON progression_history(progression_date)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_exercise_rules_user
            ON exercise_progression_rules(user_id)
        ''')

        # Insert default preferences for hardcoded user_id = 2
        print("Inserting default preferences for user_id = 2...")
        cursor.execute('''
            INSERT OR IGNORE INTO user_gym_preferences (user_id)
            VALUES (2)
        ''')

        # Also check if there are any existing workout sessions with different user_ids
        cursor.execute('SELECT DISTINCT user_id FROM workout_sessions')
        user_ids = cursor.fetchall()
        for (user_id,) in user_ids:
            cursor.execute('''
                INSERT OR IGNORE INTO user_gym_preferences (user_id)
                VALUES (?)
            ''', (user_id,))
            print(f"  - Added default preferences for user_id = {user_id}")

        conn.commit()
        print("\nMigration completed successfully!")

        # Display summary
        cursor.execute("SELECT COUNT(*) FROM user_gym_preferences")
        pref_count = cursor.fetchone()[0]
        print(f"\nSummary:")
        print(f"- Created progressive overload tables")
        print(f"- Added RPE and form quality tracking to workout sets")
        print(f"- Inserted default preferences for {pref_count} user(s)")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def rollback():
    """Rollback the migration"""
    db_path = get_db_path()
    print(f"Rolling back progressive overload migration on database: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Drop tables in reverse order due to foreign keys
        print("Dropping tables...")
        cursor.execute('DROP TABLE IF EXISTS progression_history')
        cursor.execute('DROP TABLE IF EXISTS exercise_progression_rules')
        cursor.execute('DROP TABLE IF EXISTS user_gym_preferences')

        # Note: We can't easily remove columns from workout_sets in SQLite
        # Would need to recreate the table without those columns
        print("Note: Cannot remove columns from workout_sets without recreating table")

        conn.commit()
        print("Rollback completed!")

    except sqlite3.Error as e:
        print(f"Database error during rollback: {e}")
        raise
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'rollback':
        rollback()
    else:
        migrate()
