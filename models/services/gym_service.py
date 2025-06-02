import sqlite3
import os
from datetime import datetime
from flask_login import current_user

class GymService:
    def __init__(self):
        self.db_path = os.getenv('DATABASE_PATH', 'database.db')
        # Temporary fix: hardcode user_id as 2 until proper user management is implemented
        self.user_id = 2

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
            'INSERT INTO workout_sessions (user_id, date, notes, status) VALUES (?, ?, ?, ?)',
            (self.user_id, datetime.now().date(), notes, 'in_progress')
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
        ''', (set_id, self.user_id))

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
            WHERE ws.user_id = ? AND ws.status != 'abandoned'
            GROUP BY ws.id
            ORDER BY ws.date DESC, ws.created_at DESC
            LIMIT ?
        ''', (self.user_id, limit))
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
        ''', (workout_id, self.user_id))
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

    def get_exercise_by_id(self, exercise_id):
        """Get a specific exercise by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM exercises WHERE id = ?', (exercise_id,))
        exercise = cursor.fetchone()
        conn.close()
        return exercise

    def update_exercise(self, exercise_id, name, muscle_group=None):
        """Update an exercise"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                'UPDATE exercises SET name = ?, muscle_group = ? WHERE id = ?',
                (name, muscle_group if muscle_group else None, exercise_id)
            )
            conn.commit()
            conn.close()
            return True, "Exercise updated successfully"
        except sqlite3.IntegrityError:
            conn.close()
            return False, "An exercise with this name already exists"
        except Exception as e:
            conn.close()
            return False, f"Error updating exercise: {str(e)}"

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
        ''', (workout_id, self.user_id))

        sets = cursor.fetchall()
        conn.close()

        # Group by exercise
        exercises = {}
        for set_data in sets:
            exercise_id = set_data[14]  # e.id from the join (after workout_sets columns)
            exercise_name = set_data[12]  # e.name from the join
            if exercise_id not in exercises:
                exercises[exercise_id] = {
                    'name': exercise_name,
                    'muscle_group': set_data[13],  # e.muscle_group
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
            (notes, workout_id, self.user_id)
        )
        conn.commit()
        conn.close()

    def delete_workout(self, workout_id):
        """Delete a workout and all its sets"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Check if workout belongs to user
            cursor.execute('''
                SELECT id FROM workout_sessions
                WHERE id = ? AND user_id = ?
            ''', (workout_id, self.user_id))

            if not cursor.fetchone():
                conn.close()
                return False

            # Delete all sets for this workout
            cursor.execute('DELETE FROM workout_sets WHERE session_id = ?', (workout_id,))

            # Delete the workout session
            cursor.execute('DELETE FROM workout_sessions WHERE id = ?', (workout_id,))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting workout: {e}")
            conn.rollback()
            conn.close()
            return False

    # Template Management Methods

    def create_workout_template(self, name, description=None, is_public=False):
        """Create a new workout template"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO workout_templates (name, description, user_id, is_public)
            VALUES (?, ?, ?, ?)
        ''', (name, description, self.user_id, is_public))
        template_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return template_id

    def get_user_templates(self):
        """Get all templates for the current user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT wt.*, COUNT(wte.id) as exercise_count
            FROM workout_templates wt
            LEFT JOIN workout_template_exercises wte ON wt.id = wte.template_id
            WHERE wt.user_id = ?
            GROUP BY wt.id
            ORDER BY wt.name
        ''', (self.user_id,))
        templates = cursor.fetchall()
        conn.close()
        return templates

    def get_public_templates(self):
        """Get all public templates"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT wt.*, COUNT(wte.id) as exercise_count
            FROM workout_templates wt
            LEFT JOIN workout_template_exercises wte ON wt.id = wte.template_id
            WHERE wt.is_public = 1
            GROUP BY wt.id
            ORDER BY wt.name
        ''', ())
        templates = cursor.fetchall()
        conn.close()
        return templates

    def get_template_details(self, template_id):
        """Get template details including all exercises"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Get template info
        cursor.execute('''
            SELECT * FROM workout_templates
            WHERE id = ? AND (user_id = ? OR is_public = 1)
        ''', (template_id, self.user_id))
        template = cursor.fetchone()

        if not template:
            conn.close()
            return None, []

        # Get all exercises in this template
        cursor.execute('''
            SELECT wte.*, e.name, e.muscle_group
            FROM workout_template_exercises wte
            JOIN exercises e ON wte.exercise_id = e.id
            WHERE wte.template_id = ?
            ORDER BY wte.order_index
        ''', (template_id,))
        exercises = cursor.fetchall()

        conn.close()
        return template, exercises

    def add_exercise_to_template(self, template_id, exercise_id, order_index, sets=3, target_reps=None, target_weight=None, rest_seconds=90, notes=None):
        """Add an exercise to a workout template"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Verify template belongs to user
        cursor.execute('SELECT id FROM workout_templates WHERE id = ? AND user_id = ?', (template_id, self.user_id))
        if not cursor.fetchone():
            conn.close()
            return False, "Template not found or unauthorized"

        try:
            cursor.execute('''
                INSERT INTO workout_template_exercises
                (template_id, exercise_id, order_index, sets, target_reps, target_weight, rest_seconds, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (template_id, exercise_id, order_index, sets, target_reps, target_weight, rest_seconds, notes))
            conn.commit()
            conn.close()
            return True, "Exercise added to template"
        except sqlite3.IntegrityError:
            conn.close()
            return False, "Order index already exists in template"

    def update_template_exercise(self, template_exercise_id, sets, target_reps, target_weight, rest_seconds, notes):
        """Update exercise details in a template"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Verify the template exercise belongs to user's template
        cursor.execute('''
            SELECT wte.id FROM workout_template_exercises wte
            JOIN workout_templates wt ON wte.template_id = wt.id
            WHERE wte.id = ? AND wt.user_id = ?
        ''', (template_exercise_id, self.user_id))

        if not cursor.fetchone():
            conn.close()
            return False, "Template exercise not found or unauthorized"

        cursor.execute('''
            UPDATE workout_template_exercises
            SET sets = ?, target_reps = ?, target_weight = ?, rest_seconds = ?, notes = ?
            WHERE id = ?
        ''', (sets, target_reps, target_weight, rest_seconds, notes, template_exercise_id))
        conn.commit()
        conn.close()
        return True, "Template exercise updated"

    def remove_exercise_from_template(self, template_exercise_id):
        """Remove an exercise from a template"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Verify the template exercise belongs to user's template
        cursor.execute('''
            SELECT wte.id FROM workout_template_exercises wte
            JOIN workout_templates wt ON wte.template_id = wt.id
            WHERE wte.id = ? AND wt.user_id = ?
        ''', (template_exercise_id, self.user_id))

        if not cursor.fetchone():
            conn.close()
            return False, "Template exercise not found or unauthorized"

        cursor.execute('DELETE FROM workout_template_exercises WHERE id = ?', (template_exercise_id,))
        conn.commit()
        conn.close()
        return True, "Exercise removed from template"

    def start_workout_from_template(self, template_id, notes=None):
        """Start a new workout session from a template"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Get template exercises
        cursor.execute('''
            SELECT exercise_id, sets, target_weight, target_reps
            FROM workout_template_exercises
            WHERE template_id = ?
            ORDER BY order_index
        ''', (template_id,))
        template_exercises = cursor.fetchall()

        if not template_exercises:
            conn.close()
            return None, "Template has no exercises"

        # Create workout session with 'in_progress' status
        cursor.execute('''
            INSERT INTO workout_sessions (user_id, date, notes, template_id, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (self.user_id, datetime.now().date(), notes, template_id, 'in_progress'))
        session_id = cursor.lastrowid

        # Pre-populate sets based on template
        for exercise_id, num_sets, target_weight, target_reps in template_exercises:
            for set_num in range(1, num_sets + 1):
                cursor.execute('''
                    INSERT INTO workout_sets (session_id, exercise_id, set_number, weight, reps)
                    VALUES (?, ?, ?, ?, ?)
                ''', (session_id, exercise_id, set_num, target_weight or 0, target_reps or 0))

        conn.commit()
        conn.close()
        return session_id, "Workout started from template"

    def delete_template(self, template_id):
        """Delete a workout template"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Verify template belongs to user
        cursor.execute('SELECT id FROM workout_templates WHERE id = ? AND user_id = ?', (template_id, self.user_id))
        if not cursor.fetchone():
            conn.close()
            return False, "Template not found or unauthorized"

        # Delete template (cascade will delete template exercises)
        cursor.execute('DELETE FROM workout_templates WHERE id = ?', (template_id,))
        conn.commit()
        conn.close()
        return True, "Template deleted successfully"

    def update_template(self, template_id, name, description, is_public):
        """Update template details"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE workout_templates
            SET name = ?, description = ?, is_public = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
        ''', (name, description, is_public, template_id, self.user_id))

        if cursor.rowcount > 0:
            conn.commit()
            conn.close()
            return True, "Template updated successfully"
        else:
            conn.close()
            return False, "Template not found or unauthorized"

    # Workout Completion Methods

    def complete_workout(self, workout_id):
        """Mark a workout as completed"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE workout_sessions
            SET status = 'completed', completed_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ? AND status = 'in_progress'
        ''', (workout_id, self.user_id))

        if cursor.rowcount > 0:
            # Calculate volume metrics for each exercise in the workout
            from models.services.advanced_progression_service import AdvancedProgressionService
            adv_service = AdvancedProgressionService(self.db_path)

            # Get all exercises in this workout
            cursor.execute('''
                SELECT DISTINCT exercise_id
                FROM workout_sets
                WHERE session_id = ?
            ''', (workout_id,))

            exercises = cursor.fetchall()

            # Calculate volume for each exercise
            for (exercise_id,) in exercises:
                adv_service.calculate_volume_metrics(workout_id, exercise_id)

            conn.commit()
            conn.close()
            return True, "Workout completed successfully"
        else:
            conn.close()
            return False, "Workout not found, already completed, or unauthorized"

    def abandon_workout(self, workout_id):
        """Mark a workout as abandoned"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE workout_sessions
            SET status = 'abandoned', completed_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ? AND status = 'in_progress'
        ''', (workout_id, self.user_id))

        if cursor.rowcount > 0:
            conn.commit()
            conn.close()
            return True, "Workout abandoned"
        else:
            conn.close()
            return False, "Workout not found, already completed, or unauthorized"

    def get_workout_status(self, workout_id):
        """Get the status of a workout"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT status, completed_at FROM workout_sessions
            WHERE id = ? AND user_id = ?
        ''', (workout_id, self.user_id))

        result = cursor.fetchone()
        conn.close()

        if result:
            return result[0], result[1]
        return None, None

    def get_workout_summary(self, workout_id):
        """Get summary statistics for a completed workout"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Get workout info
        cursor.execute('''
            SELECT date, created_at, completed_at, status
            FROM workout_sessions
            WHERE id = ? AND user_id = ?
        ''', (workout_id, self.user_id))

        workout_info = cursor.fetchone()
        if not workout_info:
            conn.close()
            return None

        # Calculate duration if completed
        duration = None
        if workout_info[2]:  # completed_at exists
            created = datetime.fromisoformat(workout_info[1])
            completed = datetime.fromisoformat(workout_info[2])
            duration = int((completed - created).total_seconds() / 60)  # minutes

        # Get statistics
        cursor.execute('''
            SELECT
                COUNT(DISTINCT exercise_id) as exercise_count,
                COUNT(*) as total_sets,
                SUM(weight * reps) as total_volume,
                SUM(reps) as total_reps
            FROM workout_sets
            WHERE session_id = ?
        ''', (workout_id,))

        stats = cursor.fetchone()
        conn.close()

        return {
            'date': workout_info[0],
            'status': workout_info[3],
            'duration_minutes': duration,
            'exercise_count': stats[0] or 0,
            'total_sets': stats[1] or 0,
            'total_volume': stats[2] or 0,
            'total_reps': stats[3] or 0
        }

    def create_template_from_workout(self, workout_id, name, description=None, is_public=False):
        """Create a workout template from an existing workout"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Verify workout belongs to user
            cursor.execute('''
                SELECT id FROM workout_sessions
                WHERE id = ? AND user_id = ?
            ''', (workout_id, self.user_id))

            if not cursor.fetchone():
                conn.close()
                return None, "Workout not found or unauthorized"

            # Get all exercises from the workout
            cursor.execute('''
                SELECT DISTINCT ws.exercise_id,
                       COUNT(*) as num_sets,
                       AVG(ws.weight) as avg_weight,
                       AVG(ws.reps) as avg_reps,
                       MIN(ws.set_number) as min_set_num
                FROM workout_sets ws
                WHERE ws.session_id = ?
                GROUP BY ws.exercise_id
                ORDER BY MIN(ws.id)
            ''', (workout_id,))

            exercises = cursor.fetchall()

            if not exercises:
                conn.close()
                return None, "No exercises found in workout"

            # Create the template
            cursor.execute('''
                INSERT INTO workout_templates (name, description, user_id, is_public)
                VALUES (?, ?, ?, ?)
            ''', (name, description, self.user_id, is_public))

            template_id = cursor.lastrowid

            # Add exercises to template
            for order, (exercise_id, num_sets, avg_weight, avg_reps, _) in enumerate(exercises, 1):
                cursor.execute('''
                    INSERT INTO workout_template_exercises
                    (template_id, exercise_id, order_index, sets, target_reps, target_weight, rest_seconds)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (template_id, exercise_id, order, num_sets,
                      int(round(avg_reps)), round(avg_weight, 1), 90))

            conn.commit()
            conn.close()
            return template_id, "Template created successfully"

        except sqlite3.Error as e:
            conn.rollback()
            conn.close()
            return None, f"Error creating template: {str(e)}"

    def get_last_exercise_performance(self, exercise_id):
        """Get the last performance for a specific exercise"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT
                MAX(ws.weight) as max_weight,
                MAX(ws.reps) as max_reps,
                wss.date
            FROM workout_sets ws
            JOIN workout_sessions wss ON ws.session_id = wss.id
            WHERE ws.exercise_id = ? AND wss.user_id = ?
            GROUP BY wss.id
            ORDER BY wss.date DESC, wss.id DESC
            LIMIT 1
        ''', (exercise_id, self.user_id))

        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                'max_weight': result[0],
                'max_reps': result[1],
                'workout_date': result[2]
            }
        return None
