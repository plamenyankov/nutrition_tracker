import sqlite3
import os
from datetime import datetime

# Get database path from environment or use default
DATABASE_PATH = os.getenv('DATABASE_PATH', 'database.db')

def migrate_workout_completion():
    """Add workout completion tracking fields"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(workout_sessions)")
        columns = [column[1] for column in cursor.fetchall()]

        # Add status column
        if 'status' not in columns:
            cursor.execute('''
                ALTER TABLE workout_sessions
                ADD COLUMN status TEXT DEFAULT 'completed'
            ''')
            print("✓ Added status column to workout_sessions")

            # Update existing workouts to 'completed' status
            cursor.execute('''
                UPDATE workout_sessions
                SET status = 'completed'
                WHERE status IS NULL
            ''')
            print("✓ Updated existing workouts to 'completed' status")
        else:
            print("✓ status column already exists")

        # Add completed_at column
        if 'completed_at' not in columns:
            cursor.execute('''
                ALTER TABLE workout_sessions
                ADD COLUMN completed_at TIMESTAMP
            ''')
            print("✓ Added completed_at column to workout_sessions")

            # Set completed_at for existing workouts to their created_at time
            cursor.execute('''
                UPDATE workout_sessions
                SET completed_at = created_at
                WHERE completed_at IS NULL AND status = 'completed'
            ''')
            print("✓ Set completed_at for existing completed workouts")
        else:
            print("✓ completed_at column already exists")

        # Create index for status queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_workout_sessions_status
            ON workout_sessions(status)
        ''')
        print("✓ Created index on status column")

        conn.commit()
        print("\n✅ Workout completion migration completed successfully!")
        return True

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def main():
    print(f"Running workout completion migration on database: {DATABASE_PATH}")
    print("=" * 60)
    migrate_workout_completion()

if __name__ == '__main__':
    main()
