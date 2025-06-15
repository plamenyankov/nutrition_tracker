#!/usr/bin/env python3
"""
Migrate workout data from SQLite to MySQL, excluding timing columns
"""

import os
import sys
import sqlite3
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.database.connection_manager import get_db_manager

def migrate_workout_data():
    """Migrate workout data from SQLite to MySQL development database"""
    print("="*60)
    print("MIGRATING WORKOUT DATA FROM SQLITE TO MYSQL")
    print("="*60)

    # Connect to local SQLite
    sqlite_conn = sqlite3.connect('database.db')
    sqlite_cursor = sqlite_conn.cursor()

    # Connect to MySQL development
    os.environ['FLASK_ENV'] = 'development'
    mysql_db = get_db_manager(use_mysql=True)

    try:
        with mysql_db.get_connection() as mysql_conn:
            mysql_cursor = mysql_conn.cursor()

            # Migrate workout_sessions (excluding timing columns)
            print("Migrating workout_sessions...")
            sqlite_cursor.execute("SELECT id, user_id, date, notes, created_at, template_id, status, completed_at FROM workout_sessions")
            sessions = sqlite_cursor.fetchall()

            if sessions:
                # Clear existing sessions
                mysql_cursor.execute("DELETE FROM workout_sessions")

                # Insert sessions
                mysql_cursor.executemany('''
                    INSERT INTO workout_sessions (id, user_id, date, notes, created_at, template_id, status, completed_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ''', sessions)
                print(f"✓ Migrated {len(sessions)} workout sessions")
            else:
                print("No workout sessions to migrate")

            # Migrate workout_sets (excluding timing columns)
            print("Migrating workout_sets...")
            sqlite_cursor.execute("""
                SELECT id, session_id, exercise_id, set_number, weight, reps, rpe, form_quality,
                       notes, target_reps, progression_ready, last_progression_date
                FROM workout_sets
            """)
            sets = sqlite_cursor.fetchall()

            if sets:
                # Clear existing sets
                mysql_cursor.execute("DELETE FROM workout_sets")

                # Insert sets
                mysql_cursor.executemany('''
                    INSERT INTO workout_sets (id, session_id, exercise_id, set_number, weight, reps, rpe, form_quality,
                                            notes, target_reps, progression_ready, last_progression_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', sets)
                print(f"✓ Migrated {len(sets)} workout sets")
            else:
                print("No workout sets to migrate")

            mysql_conn.commit()

            print("\n" + "="*60)
            print("✓ WORKOUT DATA MIGRATION COMPLETED!")
            print("="*60)

            # Verify migration
            mysql_cursor.execute("SELECT COUNT(*) FROM workout_sessions")
            session_count = mysql_cursor.fetchone()[0]

            mysql_cursor.execute("SELECT COUNT(*) FROM workout_sets")
            set_count = mysql_cursor.fetchone()[0]

            print(f"\nVerification:")
            print(f"  Workout sessions: {session_count}")
            print(f"  Workout sets: {set_count}")

            return True

    except Exception as e:
        print(f"Error migrating workout data: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        sqlite_conn.close()

if __name__ == "__main__":
    success = migrate_workout_data()
    sys.exit(0 if success else 1)
