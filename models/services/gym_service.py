import sqlite3
from datetime import datetime
from flask_login import current_user

class GymService:
    def __init__(self):
        self.db_path = 'database.db'

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def get_all_exercises(self):
        """Get all exercises from database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM exercises ORDER BY name')
        exercises = cursor.fetchall()
        conn.close()
        return exercises

    def add_exercise(self, name, muscle_group=None):
        """Add a new exercise"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO exercises (name, muscle_group) VALUES (?, ?)',
            (name, muscle_group)
        )
        conn.commit()
        conn.close()

    def start_workout_session(self, notes=None):
        """Start a new workout session"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO workout_sessions (user_id, date, notes) VALUES (?, ?, ?)',
            (current_user.id, datetime.now().date(), notes)
        )
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return session_id

    def log_set(self, session_id, exercise_id, set_number, weight, reps):
        """Log a single set"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO workout_sets (session_id, exercise_id, set_number, weight, reps) VALUES (?, ?, ?, ?, ?)',
            (session_id, exercise_id, set_number, weight, reps)
        )
        conn.commit()
        conn.close()

    def update_set(self, set_id, weight, reps):
        """Update an existing set"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE workout_sets SET weight = ?, reps = ? WHERE id = ?',
            (weight, reps, set_id)
        )
        conn.commit()
        conn.close()

    def delete_set(self, set_id):
        """Delete a workout set"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Check if the set belongs to the current user
        cursor.execute('''
            SELECT ws.id FROM workout_sets ws
            JOIN workout_sessions wss ON ws.session_id = wss.id
            WHERE ws.id = ? AND wss.user_id = ?
        ''', (set_id, current_user.id))

        if cursor.fetchone():
            cursor.execute('DELETE FROM workout_sets WHERE id = ?', (set_id,))
            conn.commit()
            result = True
        else:
            result = False

        conn.close()
        return result

    def get_user_workouts(self, limit=10):
        """Get user's recent workouts"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ws.*, COUNT(DISTINCT wset.exercise_id) as exercise_count
            FROM workout_sessions ws
            LEFT JOIN workout_sets wset ON ws.id = wset.session_id
            WHERE ws.user_id = ?
            GROUP BY ws.id
            ORDER BY ws.date DESC, ws.created_at DESC
            LIMIT ?
        ''', (current_user.id, limit))
        workouts = cursor.fetchall()
        conn.close()
        return workouts

    def get_workout_details(self, workout_id):
        """Get detailed information about a specific workout"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Get workout session info
        cursor.execute('''
            SELECT * FROM workout_sessions WHERE id = ? AND user_id = ?
        ''', (workout_id, current_user.id))
        workout = cursor.fetchone()

        if not workout:
            conn.close()
            return None, []

        # Get all sets for this workout
        cursor.execute('''
            SELECT ws.*, e.name, e.muscle_group
            FROM workout_sets ws
            JOIN exercises e ON ws.exercise_id = e.id
            WHERE ws.session_id = ?
            ORDER BY ws.exercise_id, ws.set_number
        ''', (workout_id,))
        sets = cursor.fetchall()

        conn.close()
        return workout, sets

    def get_exercise_by_muscle_group(self, muscle_group):
        """Get exercises filtered by muscle group"""
        conn = self.get_connection()
        cursor = conn.cursor()
        if muscle_group:
            cursor.execute('SELECT * FROM exercises WHERE muscle_group = ? ORDER BY name', (muscle_group,))
        else:
            cursor.execute('SELECT * FROM exercises ORDER BY name')
        exercises = cursor.fetchall()
        conn.close()
        return exercises

    def delete_exercise(self, exercise_id):
        """Delete an exercise (only if not used in any workouts)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Check if exercise is used in any workouts
        cursor.execute('SELECT COUNT(*) FROM workout_sets WHERE exercise_id = ?', (exercise_id,))
        count = cursor.fetchone()[0]

        if count > 0:
            conn.close()
            return False, "Cannot delete exercise that has been used in workouts"

        cursor.execute('DELETE FROM exercises WHERE id = ?', (exercise_id,))
        conn.commit()
        conn.close()
        return True, "Exercise deleted successfully"

    def get_workout_sets_grouped(self, workout_id):
        """Get workout sets grouped by exercise for editing"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT ws.*, e.name, e.muscle_group, e.id as exercise_id
            FROM workout_sets ws
            JOIN exercises e ON ws.exercise_id = e.id
            JOIN workout_sessions wss ON ws.session_id = wss.id
            WHERE ws.session_id = ? AND wss.user_id = ?
            ORDER BY ws.id
        ''', (workout_id, current_user.id))

        sets = cursor.fetchall()
        conn.close()

        # Group by exercise
        exercises = {}
        for set_data in sets:
            exercise_id = set_data[8]
            exercise_name = set_data[6]
            if exercise_id not in exercises:
                exercises[exercise_id] = {
                    'name': exercise_name,
                    'muscle_group': set_data[7],
                    'sets': []
                }
            exercises[exercise_id]['sets'].append({
                'id': set_data[0],
                'set_number': set_data[3],
                'weight': set_data[4],
                'reps': set_data[5]
            })

        return exercises

    def update_workout_notes(self, workout_id, notes):
        """Update workout session notes"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE workout_sessions SET notes = ? WHERE id = ? AND user_id = ?',
            (notes, workout_id, current_user.id)
        )
        conn.commit()
        conn.close()

    def delete_workout(self, workout_id):
        """Delete an entire workout session and all its sets"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Check if workout belongs to current user
        cursor.execute(
            'SELECT id FROM workout_sessions WHERE id = ? AND user_id = ?',
            (workout_id, current_user.id)
        )

        if not cursor.fetchone():
            conn.close()
            return False, "Workout not found or unauthorized"

        # Delete all sets first (due to foreign key constraint)
        cursor.execute('DELETE FROM workout_sets WHERE session_id = ?', (workout_id,))

        # Delete the workout session
        cursor.execute('DELETE FROM workout_sessions WHERE id = ?', (workout_id,))

        conn.commit()
        conn.close()
        return True, "Workout deleted successfully"
