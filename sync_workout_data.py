#!/usr/bin/env python3
"""
Sync workout data from production to local development database
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

def sync_workout_data():
    """Sync workout data from production to local dev database"""
    print("Syncing workout data from production...")

    # Set environment to production for MySQL connection
    os.environ['FLASK_ENV'] = 'production'
    mysql_db = get_db_manager(use_mysql=True)

    # Local SQLite connection
    sqlite_conn = sqlite3.connect('database.db')
    sqlite_cursor = sqlite_conn.cursor()

    try:
        with mysql_db.get_connection() as mysql_conn:
            mysql_cursor = mysql_conn.cursor()

            # Sync workout sessions
            print("  Syncing workout_sessions...")
            mysql_cursor.execute("SELECT * FROM workout_sessions ORDER BY date DESC LIMIT 10")
            sessions = mysql_cursor.fetchall()

            if sessions:
                # Clear existing sessions
                sqlite_cursor.execute("DELETE FROM workout_sessions")

                # Get production column info
                mysql_cursor.execute("DESCRIBE workout_sessions")
                prod_columns = mysql_cursor.fetchall()
                prod_col_names = [col[0] for col in prod_columns]

                # Get local column info
                sqlite_cursor.execute("PRAGMA table_info(workout_sessions)")
                local_columns = sqlite_cursor.fetchall()
                local_col_names = [col[1] for col in local_columns]

                print(f"    Production columns: {len(prod_col_names)} - {prod_col_names}")
                print(f"    Local columns: {len(local_col_names)} - {local_col_names}")

                # Map production data to local schema
                mapped_sessions = []
                for session in sessions:
                    mapped_session = []
                    for local_col in local_col_names:
                        if local_col in prod_col_names:
                            # Column exists in production, use its value
                            prod_index = prod_col_names.index(local_col)
                            mapped_session.append(session[prod_index])
                        else:
                            # New column not in production, use default value
                            if local_col in ['started_at', 'completed_at']:
                                mapped_session.append(None)
                            elif local_col == 'duration_seconds':
                                mapped_session.append(None)
                            elif local_col == 'status':
                                mapped_session.append('completed')  # Assume old workouts are completed
                            else:
                                mapped_session.append(None)
                    mapped_sessions.append(tuple(mapped_session))

                # Insert sessions with proper column mapping
                placeholders = ', '.join(['?'] * len(local_col_names))
                sqlite_cursor.executemany(
                    f"INSERT INTO workout_sessions VALUES ({placeholders})",
                    mapped_sessions
                )
                print(f"    ✓ Synced {len(sessions)} workout sessions")

            # Sync workout sets for these sessions
            if sessions:
                session_ids = [str(s[0]) for s in sessions]  # Get session IDs
                session_ids_str = ','.join(session_ids)

                print("  Syncing workout_sets...")
                mysql_cursor.execute(f"SELECT * FROM workout_sets WHERE session_id IN ({session_ids_str})")
                sets = mysql_cursor.fetchall()

                if sets:
                    # Clear existing sets
                    sqlite_cursor.execute("DELETE FROM workout_sets")

                    # Get production column info
                    mysql_cursor.execute("DESCRIBE workout_sets")
                    prod_columns = mysql_cursor.fetchall()
                    prod_col_names = [col[0] for col in prod_columns]

                    # Get local column info
                    sqlite_cursor.execute("PRAGMA table_info(workout_sets)")
                    local_columns = sqlite_cursor.fetchall()
                    local_col_names = [col[1] for col in local_columns]

                    print(f"    Production set columns: {len(prod_col_names)}")
                    print(f"    Local set columns: {len(local_col_names)}")

                    # Map production data to local schema
                    mapped_sets = []
                    for set_data in sets:
                        mapped_set = []
                        for local_col in local_col_names:
                            if local_col in prod_col_names:
                                # Column exists in production, use its value
                                prod_index = prod_col_names.index(local_col)
                                mapped_set.append(set_data[prod_index])
                            else:
                                # New timing columns not in production, use default values
                                if local_col in ['started_at', 'completed_at']:
                                    mapped_set.append(None)
                                elif local_col in ['duration_seconds', 'rest_duration_seconds']:
                                    mapped_set.append(None)
                                else:
                                    mapped_set.append(None)
                        mapped_sets.append(tuple(mapped_set))

                    # Insert sets with proper column mapping
                    placeholders = ', '.join(['?'] * len(local_col_names))
                    sqlite_cursor.executemany(
                        f"INSERT INTO workout_sets VALUES ({placeholders})",
                        mapped_sets
                    )
                    print(f"    ✓ Synced {len(sets)} workout sets")

            # Sync workout templates
            print("  Syncing workout_templates...")
            mysql_cursor.execute("SELECT * FROM workout_templates")
            templates = mysql_cursor.fetchall()

            if templates:
                # Clear existing templates
                sqlite_cursor.execute("DELETE FROM workout_templates")

                # Get column count
                mysql_cursor.execute("DESCRIBE workout_templates")
                columns = mysql_cursor.fetchall()
                col_count = len(columns)

                # Insert templates
                placeholders = ', '.join(['?'] * col_count)
                sqlite_cursor.executemany(
                    f"INSERT INTO workout_templates VALUES ({placeholders})",
                    templates
                )
                print(f"    ✓ Synced {len(templates)} workout templates")

                # Sync template exercises
                print("  Syncing workout_template_exercises...")
                mysql_cursor.execute("SELECT * FROM workout_template_exercises")
                template_exercises = mysql_cursor.fetchall()

                if template_exercises:
                    # Clear existing template exercises
                    sqlite_cursor.execute("DELETE FROM workout_template_exercises")

                    # Get column count
                    mysql_cursor.execute("DESCRIBE workout_template_exercises")
                    columns = mysql_cursor.fetchall()
                    col_count = len(columns)

                    # Insert template exercises
                    placeholders = ', '.join(['?'] * col_count)
                    sqlite_cursor.executemany(
                        f"INSERT INTO workout_template_exercises VALUES ({placeholders})",
                        template_exercises
                    )
                    print(f"    ✓ Synced {len(template_exercises)} template exercises")

        sqlite_conn.commit()
        print("✓ Workout data sync completed")

        # Show summary
        sqlite_cursor.execute("SELECT COUNT(*) FROM workout_sessions")
        session_count = sqlite_cursor.fetchone()[0]

        sqlite_cursor.execute("SELECT COUNT(*) FROM workout_sets")
        set_count = sqlite_cursor.fetchone()[0]

        sqlite_cursor.execute("SELECT COUNT(*) FROM workout_templates")
        template_count = sqlite_cursor.fetchone()[0]

        print(f"\nLocal database now has:")
        print(f"  - {session_count} workout sessions")
        print(f"  - {set_count} workout sets")
        print(f"  - {template_count} workout templates")

    except Exception as e:
        print(f"Error syncing workout data: {e}")
        sqlite_conn.rollback()
    finally:
        sqlite_conn.close()

if __name__ == "__main__":
    sync_workout_data()
