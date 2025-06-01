#!/usr/bin/env python3
"""
Run all migrations in the correct order
This script is safe to run multiple times - each migration checks if it needs to run
"""

import os
import sys
import sqlite3
import subprocess

DATABASE_PATH = os.getenv('DATABASE_PATH', 'database.db')

def check_migration_needed(migration_name):
    """Check if a migration needs to be run based on database schema"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Get existing tables and columns
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row[0] for row in cursor.fetchall()}

    needs_migration = False

    if migration_name == 'migrate_add_favorites.py':
        needs_migration = 'Favorites' not in tables

    elif migration_name == 'migrate_add_gym_tracker.py':
        needs_migration = 'exercises' not in tables

    elif migration_name == 'migrate_add_meal_types.py':
        if 'Consumption' in tables:
            cursor.execute("PRAGMA table_info(Consumption)")
            columns = [col[1] for col in cursor.fetchall()]
            needs_migration = 'meal_type' not in columns

    elif migration_name == 'migrate_add_recipe_consumption.py':
        needs_migration = 'recipe_consumption' not in tables

    elif migration_name == 'migrate_add_total_calories.py':
        if 'calorie_tracking' in tables:
            cursor.execute("PRAGMA table_info(calorie_tracking)")
            columns = [col[1] for col in cursor.fetchall()]
            needs_migration = 'total_calories' not in columns

    elif migration_name == 'migrate_add_workout_templates.py':
        needs_migration = 'workout_templates' not in tables

    elif migration_name == 'migrate_gym_tracker_complete.py':
        if 'workout_sessions' in tables:
            cursor.execute("PRAGMA table_info(workout_sessions)")
            columns = [col[1] for col in cursor.fetchall()]
            needs_migration = 'status' not in columns

    elif migration_name == 'migrate_workout_completion.py':
        if 'workout_sessions' in tables:
            cursor.execute("PRAGMA table_info(workout_sessions)")
            columns = [col[1] for col in cursor.fetchall()]
            needs_migration = 'completed_at' not in columns

    elif migration_name == 'migrate_progressive_overload.py':
        needs_migration = 'user_gym_preferences' not in tables

    elif migration_name == 'migrate_add_progression_priorities.py':
        if 'user_gym_preferences' in tables:
            cursor.execute("PRAGMA table_info(user_gym_preferences)")
            columns = [col[1] for col in cursor.fetchall()]
            needs_migration = 'progression_priority_1' not in columns

    elif migration_name == 'migrate_advanced_progression.py':
        if 'workout_sets' in tables:
            cursor.execute("PRAGMA table_info(workout_sets)")
            columns = [col[1] for col in cursor.fetchall()]
            needs_migration = 'rpe' not in columns

    elif migration_name == 'migrate_advanced_progression_v2.py':
        needs_migration = 'set_progression_history' not in tables

    conn.close()
    return needs_migration

def run_migration(migration_file):
    """Run a single migration file"""
    print(f"\nRunning {migration_file}...")

    if not os.path.exists(migration_file):
        print(f"⚠️  Migration file {migration_file} not found, skipping...")
        return True

    if not check_migration_needed(migration_file):
        print(f"✅ {migration_file} - Already applied, skipping...")
        return True

    try:
        result = subprocess.run([sys.executable, migration_file],
                               capture_output=True, text=True)

        if result.returncode == 0:
            print(f"✅ {migration_file} - Success!")
            if result.stdout:
                print(f"   Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {migration_file} - Failed!")
            if result.stderr:
                print(f"   Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {migration_file} - Exception: {str(e)}")
        return False

def main():
    """Run all migrations in order"""
    print(f"Running migrations for database: {DATABASE_PATH}")

    # Define migrations in order
    migrations = [
        'migrate_add_favorites.py',
        'migrate_add_gym_tracker.py',
        'migrate_add_meal_types.py',
        'migrate_add_recipe_consumption.py',
        'migrate_add_total_calories.py',
        'migrate_add_workout_templates.py',
        'migrate_gym_tracker_complete.py',
        'migrate_workout_completion.py',
        'migrate_progressive_overload.py',
        'migrate_add_progression_priorities.py',
        'migrate_advanced_progression.py',
        'migrate_advanced_progression_v2.py'
    ]

    print(f"\nFound {len(migrations)} migrations to check...")

    success_count = 0
    failed_count = 0

    for migration in migrations:
        if run_migration(migration):
            success_count += 1
        else:
            failed_count += 1

    print("\n" + "="*50)
    print(f"Migration Summary:")
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failed: {failed_count}")
    print("="*50)

    if failed_count > 0:
        sys.exit(1)
    else:
        print("\nAll migrations completed successfully!")

if __name__ == "__main__":
    main()
