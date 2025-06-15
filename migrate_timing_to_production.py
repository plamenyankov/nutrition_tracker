#!/usr/bin/env python3
"""
Apply workout timing migration to production MySQL database
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.database.connection_manager import get_db_manager

def apply_timing_migration_to_production():
    """Apply timing columns and tables to production MySQL"""
    print("="*60)
    print("APPLYING TIMING MIGRATION TO PRODUCTION MYSQL")
    print("="*60)

    # Set environment to production
    os.environ['FLASK_ENV'] = 'production'

    db_manager = get_db_manager(use_mysql=True)

    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            print("Checking current schema...")

            # Check if timing columns already exist
            cursor.execute("DESCRIBE workout_sessions")
            session_columns = [col[0] for col in cursor.fetchall()]

            cursor.execute("DESCRIBE workout_sets")
            set_columns = [col[0] for col in cursor.fetchall()]

            print(f"Current workout_sessions columns: {session_columns}")
            print(f"Current workout_sets columns: {set_columns}")

            # Add missing columns to workout_sessions
            session_timing_columns = ['started_at', 'duration_seconds']
            for col in session_timing_columns:
                if col not in session_columns:
                    print(f"Adding {col} to workout_sessions...")
                    if col == 'started_at':
                        cursor.execute("ALTER TABLE workout_sessions ADD COLUMN started_at TIMESTAMP NULL")
                    elif col == 'duration_seconds':
                        cursor.execute("ALTER TABLE workout_sessions ADD COLUMN duration_seconds INT NULL")
                    print(f"✓ Added {col} to workout_sessions")
                else:
                    print(f"  - {col} already exists in workout_sessions")

            # Add missing columns to workout_sets
            set_timing_columns = ['started_at', 'completed_at', 'duration_seconds', 'rest_duration_seconds']
            for col in set_timing_columns:
                if col not in set_columns:
                    print(f"Adding {col} to workout_sets...")
                    if col in ['started_at', 'completed_at']:
                        cursor.execute(f"ALTER TABLE workout_sets ADD COLUMN {col} TIMESTAMP NULL")
                    elif col in ['duration_seconds', 'rest_duration_seconds']:
                        cursor.execute(f"ALTER TABLE workout_sets ADD COLUMN {col} INT NULL")
                    print(f"✓ Added {col} to workout_sets")
                else:
                    print(f"  - {col} already exists in workout_sets")

            # Check if workout_timing_sessions table exists
            cursor.execute("SHOW TABLES LIKE 'workout_timing_sessions'")
            timing_table_exists = cursor.fetchone() is not None

            if not timing_table_exists:
                print("Creating workout_timing_sessions table...")
                cursor.execute('''
                    CREATE TABLE workout_timing_sessions (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        session_id INT NOT NULL,
                        event_type VARCHAR(50) NOT NULL,
                        exercise_id INT NULL,
                        set_id INT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        duration_seconds INT NULL,
                        notes TEXT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_session_id (session_id),
                        INDEX idx_event_type (event_type),
                        INDEX idx_timestamp (timestamp),
                        FOREIGN KEY (session_id) REFERENCES workout_sessions(id) ON DELETE CASCADE
                    )
                ''')
                print("✓ Created workout_timing_sessions table")
            else:
                print("  - workout_timing_sessions table already exists")

            # Create indexes for performance
            print("Creating performance indexes...")

            # Check and create indexes
            indexes_to_create = [
                ("workout_sessions", "idx_started_at", "started_at"),
                ("workout_sessions", "idx_duration", "duration_seconds"),
                ("workout_sets", "idx_set_started_at", "started_at"),
                ("workout_sets", "idx_set_completed_at", "completed_at"),
                ("workout_sets", "idx_set_duration", "duration_seconds")
            ]

            for table, index_name, column in indexes_to_create:
                try:
                    cursor.execute(f"CREATE INDEX {index_name} ON {table} ({column})")
                    print(f"✓ Created index {index_name} on {table}.{column}")
                except Exception as e:
                    if "Duplicate key name" in str(e):
                        print(f"  - Index {index_name} already exists")
                    else:
                        print(f"  - Error creating index {index_name}: {e}")

            # Update existing workout sessions to set status if NULL
            print("Updating existing workout sessions...")
            cursor.execute("""
                UPDATE workout_sessions
                SET status = 'completed'
                WHERE status IS NULL OR status = ''
            """)
            updated_sessions = cursor.rowcount
            print(f"✓ Updated {updated_sessions} workout sessions with status")

            conn.commit()

            print("\n" + "="*60)
            print("✓ TIMING MIGRATION COMPLETED SUCCESSFULLY!")
            print("="*60)

            # Show final schema
            print("\nFinal schema:")
            cursor.execute("DESCRIBE workout_sessions")
            session_cols = cursor.fetchall()
            print(f"workout_sessions columns ({len(session_cols)}):")
            for col in session_cols:
                print(f"  - {col[0]} ({col[1]})")

            cursor.execute("DESCRIBE workout_sets")
            set_cols = cursor.fetchall()
            print(f"\nworkout_sets columns ({len(set_cols)}):")
            for col in set_cols:
                print(f"  - {col[0]} ({col[1]})")

            cursor.execute("SHOW TABLES LIKE 'workout_timing_sessions'")
            if cursor.fetchone():
                cursor.execute("DESCRIBE workout_timing_sessions")
                timing_cols = cursor.fetchall()
                print(f"\nworkout_timing_sessions columns ({len(timing_cols)}):")
                for col in timing_cols:
                    print(f"  - {col[0]} ({col[1]})")

            return True

    except Exception as e:
        print(f"Error applying timing migration: {e}")
        return False

if __name__ == "__main__":
    success = apply_timing_migration_to_production()
    if success:
        print("\nProduction database is now ready for workout timing features!")
        print("You can now use the timer functionality in production.")
    else:
        print("\nMigration failed. Please check the errors above.")

    sys.exit(0 if success else 1)
