import sqlite3
import os
from datetime import datetime

# Get database path from environment or use default
DATABASE_PATH = os.getenv('DATABASE_PATH', 'database.db')

def migrate():
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

        # Insert some default templates (optional - for demo purposes)
        cursor.execute("SELECT COUNT(*) FROM workout_templates")
        if cursor.fetchone()[0] == 0:
            # Create a sample "Push Day" template
            cursor.execute('''
                INSERT INTO workout_templates (name, description, user_id, is_public)
                VALUES (?, ?, NULL, 1)
            ''', ("Push Day (Chest, Shoulders, Triceps)", "A classic push day workout focusing on chest, shoulders, and triceps", ))
            push_template_id = cursor.lastrowid

            # Get exercise IDs
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
        print("\n✅ Workout templates migration completed successfully!")

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
