#!/usr/bin/env python3
"""
Migration script to add progression priority columns and pyramid preference
to the user_gym_preferences table
"""

import sqlite3
import os

def migrate():
    # Get database path from environment or use default
    db_path = os.getenv('DATABASE_PATH', 'database.db')

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(user_gym_preferences)")
        columns = [col[1] for col in cursor.fetchall()]

        # Add missing columns
        columns_to_add = [
            ('progression_priority_1', "TEXT DEFAULT 'reps'"),
            ('progression_priority_2', "TEXT DEFAULT 'weight'"),
            ('progression_priority_3', "TEXT DEFAULT 'volume'"),
            ('progression_priority_4', "TEXT DEFAULT 'sets'"),
            ('progression_priority_5', "TEXT DEFAULT 'exercises'"),
            ('pyramid_preference', "TEXT DEFAULT 'auto_detect'")
        ]

        for column_name, column_def in columns_to_add:
            if column_name not in columns:
                print(f"Adding column {column_name}...")
                cursor.execute(f'''
                    ALTER TABLE user_gym_preferences
                    ADD COLUMN {column_name} {column_def}
                ''')
                print(f"✓ Added {column_name}")
            else:
                print(f"Column {column_name} already exists, skipping...")

        conn.commit()
        print("\n✓ Migration completed successfully!")

    except sqlite3.Error as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

    return True

if __name__ == '__main__':
    if migrate():
        print("\nYou can now access the preferences page!")
    else:
        print("\nMigration failed. Please check the error messages above.")
