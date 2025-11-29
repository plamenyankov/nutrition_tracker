import sqlite3
from datetime import datetime

class WorkoutDatabase:
    def __init__(self):
        self.conn = sqlite3.connect('workout.db', check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            week_training TEXT,
            exercise TEXT,
            sets INTEGER,
            loads TEXT,
            reps TEXT,
            load_per_exercise INTEGER
        )
        ''')
        self.conn.commit()

    def add_workout(self, date, week_training, exercise, sets, loads, reps):
        cursor = self.conn.cursor()
        
        # Calculate load per exercise
        loads_list = [int(x) for x in loads.split(',')]
        reps_list = [int(x) for x in reps.split(',')]
        load_per_exercise = sum(l * r for l, r in zip(loads_list, reps_list))

        cursor.execute('''
        INSERT INTO workouts (date, week_training, exercise, sets, loads, reps, load_per_exercise)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (date, week_training, exercise, sets, loads, reps, load_per_exercise))
        
        self.conn.commit()

    def fetch_workouts(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM workouts ORDER BY date DESC')
        columns = [description[0] for description in cursor.description]
        results = cursor.fetchall()
        return [dict(zip(columns, row)) for row in results] 