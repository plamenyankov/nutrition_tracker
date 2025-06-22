import os
import json
from datetime import datetime, timedelta
from models.database.connection_manager import get_db_manager
from models.services.progression import ProgressionService

class GymService:
    def __init__(self, user_id, connection_manager=None):
        self.user_id = user_id
        self.connection_manager = connection_manager or get_db_manager()

    def get_connection(self):
        """Get database connection"""
        return self.connection_manager.get_connection()

    def get_all_exercises(self):
        """Get all exercises"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM exercises ORDER BY name')
            exercises = cursor.fetchall()
            return exercises

    def add_exercise(self, name, muscle_group=None):
        """Add a new exercise"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO exercises (name, muscle_group) VALUES (%s, %s)', (name, muscle_group))
            conn.commit()
            return cursor.lastrowid

    def update_exercise(self, exercise_id, name, muscle_group=None):
        """Update an exercise"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE exercises SET name = %s, muscle_group = %s WHERE id = %s',
                             (name, muscle_group, exercise_id))
                conn.commit()
                return True, "Exercise updated successfully"
        except Exception as e:
            return False, f"Error updating exercise: {str(e)}"

    def delete_exercise(self, exercise_id):
        """Delete an exercise"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Check if exercise is used in any workouts
                cursor.execute('SELECT COUNT(*) FROM workout_sets WHERE exercise_id = %s', (exercise_id,))
                count = cursor.fetchone()[0]

                if count > 0:
                    return False, "Cannot delete exercise - it's used in workout history"

                cursor.execute('DELETE FROM exercises WHERE id = %s', (exercise_id,))
                conn.commit()
                return True, "Exercise deleted successfully"
        except Exception as e:
            return False, f"Error deleting exercise: {str(e)}"

    def start_workout_session(self):
        """Start a new workout session"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now()
            cursor.execute('INSERT INTO workout_sessions (user_id, date, started_at, status) VALUES (%s, %s, %s, %s)',
                         (self.user_id, now.date(), now, 'in_progress'))
            conn.commit()
            return cursor.lastrowid

    def log_set(self, session_id, exercise_id, set_number, weight, reps, duration_seconds=0):
        """Log a workout set"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO workout_sets (session_id, exercise_id, set_number, weight, reps, duration_seconds, started_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (session_id, exercise_id, set_number, weight, reps, duration_seconds, datetime.now()))
            conn.commit()
            return cursor.lastrowid

    def update_set(self, set_id, weight, reps):
        """Update a workout set"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE workout_sets SET weight = %s, reps = %s WHERE id = %s',
                         (weight, reps, set_id))
            conn.commit()

    def delete_set(self, set_id):
        """Delete a workout set"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Verify the set belongs to the current user
            cursor.execute('''
                SELECT ws.id FROM workout_sets ws
                JOIN workout_sessions wss ON ws.session_id = wss.id
                WHERE ws.id = %s AND wss.user_id = %s
            ''', (set_id, self.user_id))

            if cursor.fetchone():
                cursor.execute('DELETE FROM workout_sets WHERE id = %s', (set_id,))
                conn.commit()
                return True
            return False

    def get_user_workouts(self, limit=20):
        """Get user's workout history"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT ws.id, ws.user_id, ws.date, ws.started_at, ws.completed_at, ws.status, ws.notes,
                       COUNT(wset.id) as total_sets,
                       SUM(wset.weight * wset.reps) as total_volume
                FROM workout_sessions ws
                LEFT JOIN workout_sets wset ON ws.id = wset.session_id
                WHERE ws.user_id = %s
                GROUP BY ws.id, ws.user_id, ws.date, ws.started_at, ws.completed_at, ws.status, ws.notes
                ORDER BY ws.date DESC, ws.id DESC
                LIMIT %s
            ''', (self.user_id, limit))
            return cursor.fetchall()

    def get_workout_details(self, workout_id):
        """Get detailed workout information"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Get workout session
            cursor.execute('SELECT * FROM workout_sessions WHERE id = %s AND user_id = %s',
                         (workout_id, self.user_id))
            workout = cursor.fetchone()

            if not workout:
                return None, []

            # Get workout sets with exercise details
            cursor.execute('''
                SELECT ws.*, e.name, e.muscle_group
                FROM workout_sets ws
                JOIN exercises e ON ws.exercise_id = e.id
                WHERE ws.session_id = %s
                ORDER BY ws.exercise_id, ws.set_number
            ''', (workout_id,))
            sets = cursor.fetchall()

            return workout, sets

    def complete_workout(self, workout_id):
        """Mark workout as completed"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE workout_sessions
                    SET completed_at = %s, status = 'completed'
                    WHERE id = %s AND user_id = %s
                ''', (datetime.now(), workout_id, self.user_id))
                conn.commit()

                if cursor.rowcount > 0:
                    return True, "Workout completed successfully"
                else:
                    return False, "Workout not found or unauthorized"
        except Exception as e:
            return False, f"Error completing workout: {str(e)}"

    def abandon_workout(self, workout_id):
        """Abandon a workout"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE workout_sessions
                    SET status = 'abandoned'
                    WHERE id = %s AND user_id = %s
                ''', (workout_id, self.user_id))
                conn.commit()

                if cursor.rowcount > 0:
                    return True, "Workout abandoned"
                else:
                    return False, "Workout not found or unauthorized"
        except Exception as e:
            return False, f"Error abandoning workout: {str(e)}"

    def get_workout_summary(self, workout_id):
        """Get workout summary statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT
                    ws.started_at,
                    ws.completed_at,
                    COUNT(wset.id) as total_sets,
                    SUM(wset.weight * wset.reps) as total_volume,
                    COUNT(DISTINCT wset.exercise_id) as exercises_count
                FROM workout_sessions ws
                LEFT JOIN workout_sets wset ON ws.id = wset.session_id
                WHERE ws.id = %s AND ws.user_id = %s
                GROUP BY ws.id, ws.started_at, ws.completed_at
            ''', (workout_id, self.user_id))

            result = cursor.fetchone()
            if result:
                duration = 0
                if result[1] and result[0]:  # completed_at and started_at
                    duration = (result[1] - result[0]).total_seconds() / 60

                return {
                    'duration_minutes': int(duration),
                    'total_sets': result[2] or 0,
                    'total_volume': result[3] or 0,
                    'exercises_count': result[4] or 0
                }
            return {}

    def delete_workout(self, workout_id):
        """Delete a workout and all its sets"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # First delete all sets
                cursor.execute('''
                    DELETE ws FROM workout_sets ws
                    JOIN workout_sessions wss ON ws.session_id = wss.id
                    WHERE wss.id = %s AND wss.user_id = %s
                ''', (workout_id, self.user_id))

                # Then delete the session
                cursor.execute('DELETE FROM workout_sessions WHERE id = %s AND user_id = %s',
                             (workout_id, self.user_id))
                conn.commit()

                return cursor.rowcount > 0
        except Exception as e:
            return False

    def get_exercise_by_muscle_group(self, muscle_group):
        """Get exercises filtered by muscle group"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if muscle_group:
                cursor.execute('SELECT * FROM exercises WHERE muscle_group = %s ORDER BY name', (muscle_group,))
            else:
                cursor.execute('SELECT * FROM exercises ORDER BY name')
            exercises = cursor.fetchall()
            return exercises

    def get_exercise_by_id(self, exercise_id):
        """Get a specific exercise by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM exercises WHERE id = %s', (exercise_id,))
            exercise = cursor.fetchone()
            return exercise

    def update_workout_notes(self, workout_id, notes):
        """Update workout notes"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE workout_sessions
                SET notes = %s
                WHERE id = %s AND user_id = %s
            ''', (notes, workout_id, self.user_id))
            conn.commit()

    def get_workout_status(self, workout_id):
        """Get workout status and completion time"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT status, completed_at
                FROM workout_sessions
                WHERE id = %s AND user_id = %s
            ''', (workout_id, self.user_id))

            result = cursor.fetchone()
            if result:
                return result[0] or 'in_progress', result[1]
            return None, None

    def get_workout_sets_grouped(self, workout_id):
        """Get workout sets grouped by exercise for editing"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT ws.*, e.name, e.muscle_group, e.id as exercise_id
                FROM workout_sets ws
                JOIN exercises e ON ws.exercise_id = e.id
                JOIN workout_sessions wss ON ws.session_id = wss.id
                WHERE ws.session_id = %s AND wss.user_id = %s
                ORDER BY ws.id
            ''', (workout_id, self.user_id))

            sets = cursor.fetchall()

        # Group by exercise
        exercises = {}
        for set_data in sets:
            exercise_id = set_data[18]  # e.id from the join (after workout_sets columns)
            exercise_name = set_data[16]  # e.name from the join
            if exercise_id not in exercises:
                exercises[exercise_id] = {
                    'name': exercise_name,
                    'muscle_group': set_data[17],  # e.muscle_group
                    'sets': []
                }
            exercises[exercise_id]['sets'].append({
                'id': set_data[0],
                'set_number': set_data[3],
                'weight': set_data[4],
                'reps': set_data[5]
            })

        return exercises

    # Template methods
    def get_user_templates(self):
        """Get user's workout templates"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT wt.*, COUNT(wte.id) as exercise_count
                FROM workout_templates wt
                LEFT JOIN workout_template_exercises wte ON wt.id = wte.template_id
                WHERE wt.user_id = %s AND wt.is_public = FALSE
                GROUP BY wt.id
                ORDER BY wt.created_at DESC
            ''', (self.user_id,))
            return cursor.fetchall()

    def get_public_templates(self):
        """Get public workout templates"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT wt.*, COUNT(wte.id) as exercise_count
                FROM workout_templates wt
                LEFT JOIN workout_template_exercises wte ON wt.id = wte.template_id
                WHERE wt.is_public = TRUE
                GROUP BY wt.id
                ORDER BY wt.created_at DESC
                LIMIT 10
            ''', ())
            return cursor.fetchall()

    def create_template(self, name, description, is_public=False):
        """Create a new workout template"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO workout_templates (user_id, name, description, is_public, created_at)
                VALUES (%s, %s, %s, %s, %s)
            ''', (self.user_id, name, description, is_public, datetime.now()))
            conn.commit()
            return cursor.lastrowid

    def get_template_by_id(self, template_id):
        """Get template by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM workout_templates WHERE id = %s', (template_id,))
            return cursor.fetchone()

    def get_template_exercises(self, template_id):
        """Get exercises for a template"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT wte.*, e.name, e.muscle_group
                FROM workout_template_exercises wte
                JOIN exercises e ON wte.exercise_id = e.id
                WHERE wte.template_id = %s
                ORDER BY wte.order_index
            ''', (template_id,))
            return cursor.fetchall()

    def add_exercise_to_template(self, template_id, exercise_id, sets, target_reps, target_weight, rest_seconds, notes, order_index):
        """Add exercise to template"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO workout_template_exercises
                (template_id, exercise_id, sets, target_reps, target_weight, rest_seconds, notes, order_index)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (template_id, exercise_id, sets, target_reps, target_weight, rest_seconds, notes, order_index))
            conn.commit()
            return cursor.lastrowid

    def update_template_exercise(self, template_exercise_id, sets, target_reps, target_weight, rest_seconds, notes):
        """Update template exercise"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE workout_template_exercises
                SET sets = %s, target_reps = %s, target_weight = %s, rest_seconds = %s, notes = %s
                WHERE id = %s
            ''', (sets, target_reps, target_weight, rest_seconds, notes, template_exercise_id))
            conn.commit()

    def remove_exercise_from_template(self, template_exercise_id):
        """Remove exercise from template"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM workout_template_exercises WHERE id = %s', (template_exercise_id,))
            conn.commit()

    def delete_template(self, template_id):
        """Delete template and its exercises"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # First delete template exercises
                cursor.execute('DELETE FROM workout_template_exercises WHERE template_id = %s', (template_id,))

                # Then delete template (only if user owns it)
                cursor.execute('DELETE FROM workout_templates WHERE id = %s AND user_id = %s',
                             (template_id, self.user_id))
                conn.commit()

                return cursor.rowcount > 0
        except Exception as e:
            return False

    def start_workout_from_template(self, template_id):
        """Start a new workout from a template"""
        template = self.get_template_by_id(template_id)
        if not template:
            return None

        # Create new workout session
        session_id = self.start_workout_session()
        return session_id

    def create_template_from_workout(self, workout_id, name, description):
        """Create a template from an existing workout"""
        workout, sets = self.get_workout_details(workout_id)
        if not workout:
            return None

        # Create template
        template_id = self.create_template(name, description)

        # Group sets by exercise and add to template
        exercises = {}
        for set_data in sets:
            exercise_id = set_data[2]  # exercise_id column
            if exercise_id not in exercises:
                exercises[exercise_id] = {
                    'sets': 0,
                    'weights': [],
                    'reps': []
                }
            exercises[exercise_id]['sets'] += 1
            exercises[exercise_id]['weights'].append(set_data[4])  # weight
            exercises[exercise_id]['reps'].append(set_data[5])     # reps

        # Add exercises to template
        order_index = 1
        for exercise_id, data in exercises.items():
            avg_weight = sum(data['weights']) / len(data['weights']) if data['weights'] else 0
            avg_reps = sum(data['reps']) / len(data['reps']) if data['reps'] else 0

            self.add_exercise_to_template(
                template_id, exercise_id, data['sets'],
                int(avg_reps), avg_weight, 90, "", order_index
            )
            order_index += 1

        return template_id

    def update_template(self, template_id, name, description):
        """Update template details"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE workout_templates
                SET name = %s, description = %s
                WHERE id = %s AND user_id = %s
            ''', (name, description, template_id, self.user_id))
            conn.commit()
            return cursor.rowcount > 0

    def get_exercise_history(self, exercise_id, limit=10):
        """Get recent history for an exercise"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT ws.weight, ws.reps, ws.started_at, wss.started_at, wss.date
                FROM workout_sets ws
                JOIN workout_sessions wss ON ws.session_id = wss.id
                WHERE ws.exercise_id = %s AND wss.user_id = %s
                ORDER BY wss.date DESC, ws.id DESC
                LIMIT %s
            ''', (exercise_id, self.user_id, limit))
            return cursor.fetchall()

    def get_exercise_progression_data(self, exercise_id):
        """Get progression data for an exercise"""
        history = self.get_exercise_history(exercise_id, 50)
        if not history:
            return None

        # Calculate progression metrics
        weights = [h[0] for h in history if h[0]]
        if not weights:
            return None

        return {
            'current_max': max(weights),
            'recent_average': sum(weights[-5:]) / len(weights[-5:]) if len(weights) >= 5 else sum(weights) / len(weights),
            'total_workouts': len(history),
            'last_workout': history[0] if history else None
        }

    def get_quick_progression_info(self, exercise_id):
        """Get quick progression info for exercise"""
        history = self.get_exercise_history(exercise_id, 5)
        if not history:
            return {'has_history': False}

        last_set = history[0]
        return {
            'has_history': True,
            'last_weight': last_set[0],
            'last_reps': last_set[1],
            'ready_for_progression': len(history) >= 3  # Simple progression logic
        }

    def get_last_exercise_performance(self, exercise_id):
        """Get the last performance for an exercise"""
        history = self.get_exercise_history(exercise_id, 1)
        if not history:
            return None

        last_set = history[0]
        return {
            'weight': last_set[0],
            'reps': last_set[1],
            'logged_at': last_set[2],
            'started_at': last_set[3] if len(last_set) > 3 else None,
            'workout_date': last_set[4] if len(last_set) > 4 else None
        }
