import sqlite3

def migrate():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Create exercises table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            muscle_group TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

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

    conn.commit()
    conn.close()

if __name__ == '__main__':
    migrate()
    print("Gym tracker tables created successfully!")
