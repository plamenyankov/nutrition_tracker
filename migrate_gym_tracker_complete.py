import sqlite3
import os
from datetime import datetime

# Get database path from environment or use default
DATABASE_PATH = os.getenv('DATABASE_PATH', 'database.db')

def migrate_gym_tracker():
    """Create the basic gym tracker tables"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        # Create exercises table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                muscle_group TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✓ Created exercises table")

        # Create workout_sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workout_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                date DATE NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        print("✓ Created workout_sessions table")

        # Create workout_sets table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workout_sets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                exercise_id INTEGER,
                set_number INTEGER,
                weight REAL,
                reps INTEGER,
                FOREIGN KEY (session_id) REFERENCES workout_sessions(id),
                FOREIGN KEY (exercise_id) REFERENCES exercises(id)
            )
        ''')
        print("✓ Created workout_sets table")

        # Populate initial exercises
        exercises = [
            ('Squat', 'Legs'),
            ('Bench Press', 'Chest'),
            ('Deadlift', 'Back'),
            ('Overhead Press', 'Shoulders'),
            ('Barbell Curls', 'Biceps'),
            ('Rope Pushdown', 'Triceps'),
            ('Leg Press', 'Legs'),
            ('Lat Pull Down', 'Back'),
            ('Dumbbell Press', 'Chest'),
            ('Leg Curls', 'Legs'),
            ('Incline Bench Press', 'Chest'),
            ('Leg Extension', 'Legs'),
            ('Romanian Deadlift', 'Back'),
            ('Calves', 'Legs'),
            ('Abs', 'Core')
        ]

        cursor.executemany(
            'INSERT OR IGNORE INTO exercises (name, muscle_group) VALUES (?, ?)',
            exercises
        )
        print("✓ Populated initial exercises")

        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"❌ Error creating gym tracker tables: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def migrate_workout_templates():
    """Add workout templates functionality"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        # Create workout_templates table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workout_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                user_id INTEGER,
                is_public BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        print("✓ Created workout_templates table")

        # Create workout_template_exercises table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workout_template_exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER NOT NULL,
                exercise_id INTEGER NOT NULL,
                order_index INTEGER NOT NULL,
                sets INTEGER DEFAULT 3,
                target_reps INTEGER,
                target_weight REAL,
                rest_seconds INTEGER DEFAULT 90,
                notes TEXT,
                FOREIGN KEY (template_id) REFERENCES workout_templates(id) ON DELETE CASCADE,
                FOREIGN KEY (exercise_id) REFERENCES exercises(id),
                UNIQUE(template_id, order_index)
            )
        ''')
        print("✓ Created workout_template_exercises table")

        # Add template_id to workout_sessions if it doesn't exist
        cursor.execute("PRAGMA table_info(workout_sessions)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'template_id' not in columns:
            cursor.execute('''
                ALTER TABLE workout_sessions
                ADD COLUMN template_id INTEGER REFERENCES workout_templates(id)
            ''')
            print("✓ Added template_id column to workout_sessions")
        else:
            print("✓ template_id column already exists in workout_sessions")

        # Create indexes for better performance
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_workout_templates_user
            ON workout_templates(user_id)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_workout_template_exercises_template
            ON workout_template_exercises(template_id)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_workout_sessions_template
            ON workout_sessions(template_id)
        ''')
        print("✓ Created indexes")

        # Insert sample template only if none exist
        cursor.execute("SELECT COUNT(*) FROM workout_templates")
        if cursor.fetchone()[0] == 0:
            # Create a sample "Push Day" template
            cursor.execute('''
                INSERT INTO workout_templates (name, description, user_id, is_public)
                VALUES (?, ?, NULL, 1)
            ''', ("Push Day (Chest, Shoulders, Triceps)", "A classic push day workout focusing on chest, shoulders, and triceps", ))
            push_template_id = cursor.lastrowid

            # Add exercises to the template
            exercises_to_add = [
                ("Bench Press", 4, 10, 60.0, 120),
                ("Incline Bench Press", 3, 12, 50.0, 90),
                ("Overhead Press", 4, 8, 40.0, 120),
                ("Rope Pushdown", 3, 15, 20.0, 60),
            ]

            order = 1
            for exercise_name, sets, reps, weight, rest in exercises_to_add:
                cursor.execute("SELECT id FROM exercises WHERE name = ?", (exercise_name,))
                result = cursor.fetchone()
                if result:
                    exercise_id = result[0]
                    cursor.execute('''
                        INSERT INTO workout_template_exercises
                        (template_id, exercise_id, order_index, sets, target_reps, target_weight, rest_seconds)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (push_template_id, exercise_id, order, sets, reps, weight, rest))
                    order += 1

            print("✓ Created sample 'Push Day' template")

        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"❌ Error creating workout templates: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def main():
    print(f"Running gym tracker migrations on database: {DATABASE_PATH}")
    print("=" * 60)

    # Step 1: Create basic gym tracker tables
    print("\nStep 1: Creating gym tracker tables...")
    if migrate_gym_tracker():
        print("✅ Gym tracker tables created successfully!")
    else:
        print("❌ Failed to create gym tracker tables. Aborting.")
        return

    # Step 2: Add workout templates
    print("\nStep 2: Adding workout templates functionality...")
    if migrate_workout_templates():
        print("✅ Workout templates migration completed successfully!")
    else:
        print("❌ Failed to add workout templates.")
        return

    print("\n" + "=" * 60)
    print("✅ All gym tracker migrations completed successfully!")

if __name__ == '__main__':
    main()
