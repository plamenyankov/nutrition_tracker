#!/usr/bin/env python3
"""
Migration script to add workout timing functionality
Adds columns for tracking workout duration and individual set timing
"""

import sqlite3
import os
from datetime import datetime

def migrate():
    """Add timing columns to workout tables"""
    # Get database path from environment or use default
    db_path = os.getenv('DATABASE_PATH', 'database.db')

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        print("Adding timing columns to workout tables...")

        # Check existing columns in workout_sessions
        cursor.execute("PRAGMA table_info(workout_sessions)")
        session_columns = [col[1] for col in cursor.fetchall()]

        # Add timing columns to workout_sessions
        session_additions = [
            ('started_at', 'TIMESTAMP'),
            ('completed_at', 'TIMESTAMP'),
            ('duration_seconds', 'INTEGER'),
            ('status', 'TEXT DEFAULT "in_progress"')  # 'in_progress', 'completed', 'abandoned'
        ]

        for column_name, column_def in session_additions:
            if column_name not in session_columns:
                cursor.execute(f'ALTER TABLE workout_sessions ADD COLUMN {column_name} {column_def}')
                print(f"✓ Added {column_name} to workout_sessions")
            else:
                print(f"  - {column_name} already exists in workout_sessions")

        # Check existing columns in workout_sets
        cursor.execute("PRAGMA table_info(workout_sets)")
        sets_columns = [col[1] for col in cursor.fetchall()]

        # Add timing columns to workout_sets
        sets_additions = [
            ('started_at', 'TIMESTAMP'),
            ('completed_at', 'TIMESTAMP'),
            ('duration_seconds', 'INTEGER'),
            ('rest_duration_seconds', 'INTEGER')  # Time between this set and the next
        ]

        for column_name, column_def in sets_additions:
            if column_name not in sets_columns:
                cursor.execute(f'ALTER TABLE workout_sets ADD COLUMN {column_name} {column_def}')
                print(f"✓ Added {column_name} to workout_sets")
            else:
                print(f"  - {column_name} already exists in workout_sets")

        # Create workout_timing_sessions table for detailed timing tracking
        print("\nCreating workout_timing_sessions table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workout_timing_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                event_type TEXT NOT NULL, -- 'workout_start', 'workout_pause', 'workout_resume', 'workout_complete', 'set_start', 'set_complete', 'rest_start', 'rest_complete'
                exercise_id INTEGER,
                set_id INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                duration_seconds INTEGER, -- For completed events
                notes TEXT,
                FOREIGN KEY (session_id) REFERENCES workout_sessions(id) ON DELETE CASCADE,
                FOREIGN KEY (exercise_id) REFERENCES exercises(id),
                FOREIGN KEY (set_id) REFERENCES workout_sets(id)
            )
        ''')
        print("✓ Created workout_timing_sessions table")

        # Create indexes for better performance
        print("\nCreating indexes...")
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timing_session_id
            ON workout_timing_sessions(session_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timing_event_type
            ON workout_timing_sessions(event_type, timestamp)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_workout_sessions_status
            ON workout_sessions(status)
        ''')
        print("✓ Created indexes")

        # Update existing workout_sessions to have 'completed' status if they have sets
        print("\nUpdating existing workout sessions...")
        cursor.execute('''
            UPDATE workout_sessions
            SET status = 'completed'
            WHERE id IN (
                SELECT DISTINCT session_id
                FROM workout_sets
            ) AND status IS NULL
        ''')

        # Set started_at for existing sessions based on created_at
        cursor.execute('''
            UPDATE workout_sessions
            SET started_at = created_at
            WHERE started_at IS NULL AND created_at IS NOT NULL
        ''')

        updated_sessions = cursor.rowcount
        print(f"✓ Updated {updated_sessions} existing workout sessions")

        conn.commit()
        print("\n✓ Workout timing migration completed successfully!")

        # Display summary
        cursor.execute("SELECT COUNT(*) FROM workout_sessions")
        total_sessions = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM workout_sets")
        total_sets = cursor.fetchone()[0]

        print(f"\nDatabase summary:")
        print(f"  - Total workout sessions: {total_sessions}")
        print(f"  - Total workout sets: {total_sets}")
        print(f"  - Timing tracking enabled for future workouts")

    except sqlite3.Error as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

    return True

if __name__ == "__main__":
    success = migrate()
    if success:
        print("\nMigration completed successfully!")
    else:
        print("\nMigration failed!")
        exit(1)
