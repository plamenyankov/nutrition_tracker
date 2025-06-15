import os
from datetime import datetime
from flask_login import current_user
from models.database.connection_manager import DatabaseConnectionManager

class GymService:
    def __init__(self):
        self.connection_manager = DatabaseConnectionManager(use_mysql=True)
        # Temporary fix: hardcode user_id as 2 until proper user management is implemented
        self.user_id = 2

    def get_connection(self):
        return self.connection_manager.get_connection()

    def get_all_exercises(self):
        """Get all exercises from database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM exercises ORDER BY name')
            exercises = cursor.fetchall()
            return exercises

    def add_exercise(self, name, muscle_group=None):
        """Add a new exercise"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if self.connection_manager.use_mysql:
                cursor.execute(
                    'INSERT INTO exercises (name, muscle_group) VALUES (%s, %s)',
                    (name, muscle_group)
                )
            else:
                cursor.execute(
                    'INSERT INTO exercises (name, muscle_group) VALUES (?, ?)',
                    (name, muscle_group)
                )

    def start_workout_session(self, notes=None):
        """Start a new workout session"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if self.connection_manager.use_mysql:
                cursor.execute(
                    'INSERT INTO workout_sessions (user_id, date, notes, status) VALUES (%s, %s, %s, %s)',
                    (self.user_id, datetime.now().date(), notes, 'in_progress')
                )
            else:
                cursor.execute(
                    'INSERT INTO workout_sessions (user_id, date, notes, status) VALUES (?, ?, ?, ?)',
                    (self.user_id, datetime.now().date(), notes, 'in_progress')
                )
            session_id = cursor.lastrowid
            conn.commit()
            return session_id

    def log_set(self, session_id, exercise_id, set_number, weight, reps, duration_seconds=0, start_timer=True):
        """Log a single set with optional timing"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Insert the set
            if self.connection_manager.use_mysql:
                cursor.execute(
                    'INSERT INTO workout_sets (session_id, exercise_id, set_number, weight, reps, started_at, duration_seconds) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                    (session_id, exercise_id, set_number, weight, reps, datetime.now() if start_timer else None, duration_seconds)
                )
            else:
                cursor.execute(
                    'INSERT INTO workout_sets (session_id, exercise_id, set_number, weight, reps, started_at, duration_seconds) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (session_id, exercise_id, set_number, weight, reps, datetime.now() if start_timer else None, duration_seconds)
                )

            set_id = cursor.lastrowid
            conn.commit()

            return set_id

    def update_set(self, set_id, weight, reps):
        """Update an existing set"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if self.connection_manager.use_mysql:
                cursor.execute(
                    'UPDATE workout_sets SET weight = %s, reps = %s WHERE id = %s',
                    (weight, reps, set_id)
                )
            else:
                cursor.execute(
                    'UPDATE workout_sets SET weight = ?, reps = ? WHERE id = ?',
                    (weight, reps, set_id)
                )

    def delete_set(self, set_id):
        """Delete a workout set"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Check if the set belongs to the current user
            if self.connection_manager.use_mysql:
                cursor.execute('''
                    SELECT ws.id FROM workout_sets ws
                    JOIN workout_sessions wss ON ws.session_id = wss.id
                    WHERE ws.id = %s AND wss.user_id = %s
                ''', (set_id, self.user_id))

                if cursor.fetchone():
                    cursor.execute('DELETE FROM workout_sets WHERE id = %s', (set_id,))
                    result = True
                else:
                    result = False
            else:
                cursor.execute('''
                    SELECT ws.id FROM workout_sets ws
                    JOIN workout_sessions wss ON ws.session_id = wss.id
                    WHERE ws.id = ? AND wss.user_id = ?
                ''', (set_id, self.user_id))

                if cursor.fetchone():
                    cursor.execute('DELETE FROM workout_sets WHERE id = ?', (set_id,))
                    result = True
                else:
                    result = False

            return result

    def get_user_workouts(self, limit=10):
        """Get user's recent workouts"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if self.connection_manager.use_mysql:
                cursor.execute('''
                    SELECT ws.*, COUNT(DISTINCT wset.exercise_id) as exercise_count
                    FROM workout_sessions ws
                    LEFT JOIN workout_sets wset ON ws.id = wset.session_id
                    WHERE ws.user_id = %s
                    GROUP BY ws.id
                    ORDER BY ws.date DESC, ws.created_at DESC
                    LIMIT %s
                ''', (self.user_id, limit))
            else:
                cursor.execute('''
                    SELECT ws.*, COUNT(DISTINCT wset.exercise_id) as exercise_count
                    FROM workout_sessions ws
                    LEFT JOIN workout_sets wset ON ws.id = wset.session_id
                    WHERE ws.user_id = ?
                    GROUP BY ws.id
                    ORDER BY ws.date DESC, ws.created_at DESC
                    LIMIT ?
                ''', (self.user_id, limit))
            workouts = cursor.fetchall()
            return workouts

    def get_workout_details(self, workout_id):
        """Get detailed information about a specific workout"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Get workout session info
            if self.connection_manager.use_mysql:
                cursor.execute('''
                    SELECT * FROM workout_sessions WHERE id = %s AND user_id = %s
                ''', (workout_id, self.user_id))
                workout = cursor.fetchone()

                if not workout:
                    return None, []

                # Get all sets for this workout
                cursor.execute('''
                    SELECT ws.*, e.name, e.muscle_group
                    FROM workout_sets ws
                    JOIN exercises e ON ws.exercise_id = e.id
                    WHERE ws.session_id = %s
                    ORDER BY ws.exercise_id, ws.set_number
                ''', (workout_id,))
                sets = cursor.fetchall()
            else:
                cursor.execute('''
                    SELECT * FROM workout_sessions WHERE id = ? AND user_id = ?
                ''', (workout_id, self.user_id))
                workout = cursor.fetchone()

                if not workout:
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

            return workout, sets

    def get_exercise_by_muscle_group(self, muscle_group):
        """Get exercises filtered by muscle group"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if muscle_group:
                if self.connection_manager.use_mysql:
                    cursor.execute('SELECT * FROM exercises WHERE muscle_group = %s ORDER BY name', (muscle_group,))
                else:
                    cursor.execute('SELECT * FROM exercises WHERE muscle_group = ? ORDER BY name', (muscle_group,))
            else:
                cursor.execute('SELECT * FROM exercises ORDER BY name')
            exercises = cursor.fetchall()
            return exercises

    def get_exercise_by_id(self, exercise_id):
        """Get a specific exercise by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if self.connection_manager.use_mysql:
                cursor.execute('SELECT * FROM exercises WHERE id = %s', (exercise_id,))
            else:
                cursor.execute('SELECT * FROM exercises WHERE id = ?', (exercise_id,))
            exercise = cursor.fetchone()
            return exercise

    def update_exercise(self, exercise_id, name, muscle_group=None):
        """Update an exercise"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if self.connection_manager.use_mysql:
                cursor.execute('''
                    UPDATE exercises
                    SET name = %s, muscle_group = %s
                    WHERE id = %s
                ''', (name, muscle_group, exercise_id))
            else:
                cursor.execute('''
                    UPDATE exercises
                    SET name = ?, muscle_group = ?
                    WHERE id = ?
                ''', (name, muscle_group, exercise_id))

            if cursor.rowcount > 0:
                conn.commit()
                return True, "Exercise updated successfully"
            else:
                return False, "Exercise not found"

    def delete_exercise(self, exercise_id):
        """Delete an exercise"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                if self.connection_manager.use_mysql:
                    cursor.execute('DELETE FROM exercises WHERE id = %s', (exercise_id,))
                else:
                    cursor.execute('DELETE FROM exercises WHERE id = ?', (exercise_id,))

                if cursor.rowcount > 0:
                    conn.commit()
                    return True, "Exercise deleted successfully"
                else:
                    return False, "Exercise not found"
            except Exception as e:
                conn.rollback()
                return False, f"Cannot delete exercise: {str(e)}"

    def get_workout_sets_grouped(self, workout_id):
        """Get workout sets grouped by exercise for editing"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if self.connection_manager.use_mysql:
                cursor.execute('''
                    SELECT ws.*, e.name, e.muscle_group, e.id as exercise_id
                    FROM workout_sets ws
                    JOIN exercises e ON ws.exercise_id = e.id
                    JOIN workout_sessions wss ON ws.session_id = wss.id
                    WHERE ws.session_id = %s AND wss.user_id = %s
                    ORDER BY ws.id
                ''', (workout_id, self.user_id))
            else:
                cursor.execute('''
                    SELECT ws.*, e.name, e.muscle_group, e.id as exercise_id
                    FROM workout_sets ws
                    JOIN exercises e ON ws.exercise_id = e.id
                    JOIN workout_sessions wss ON ws.session_id = wss.id
                    WHERE ws.session_id = ? AND wss.user_id = ?
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

    def update_workout_notes(self, workout_id, notes):
        """Update workout notes"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if self.connection_manager.use_mysql:
                cursor.execute('''
                    UPDATE workout_sessions
                    SET notes = %s
                    WHERE id = %s AND user_id = %s
                ''', (notes, workout_id, self.user_id))
            else:
                cursor.execute('''
                    UPDATE workout_sessions
                    SET notes = ?
                    WHERE id = ? AND user_id = ?
                ''', (notes, workout_id, self.user_id))

            if cursor.rowcount > 0:
                conn.commit()
                return True, "Notes updated successfully"
            else:
                return False, "Workout not found or unauthorized"

    def delete_workout(self, workout_id):
        """Delete a workout session and all its sets"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                # Verify workout belongs to user
                if self.connection_manager.use_mysql:
                    cursor.execute('SELECT id FROM workout_sessions WHERE id = %s AND user_id = %s', (workout_id, self.user_id))
                else:
                    cursor.execute('SELECT id FROM workout_sessions WHERE id = ? AND user_id = ?', (workout_id, self.user_id))

                if not cursor.fetchone():
                    return False

                # Delete all sets for this workout
                if self.connection_manager.use_mysql:
                    cursor.execute('DELETE FROM workout_sets WHERE session_id = %s', (workout_id,))
                    cursor.execute('DELETE FROM workout_sessions WHERE id = %s', (workout_id,))
                else:
                    cursor.execute('DELETE FROM workout_sets WHERE session_id = ?', (workout_id,))
                    cursor.execute('DELETE FROM workout_sessions WHERE id = ?', (workout_id,))

                conn.commit()
                return True
            except Exception as e:
                print(f"Error deleting workout: {e}")
                conn.rollback()
                return False

    # Template Management Methods

    def create_workout_template(self, name, description=None, is_public=False):
        """Create a new workout template"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if self.connection_manager.use_mysql:
                cursor.execute('''
                    INSERT INTO workout_templates (name, description, user_id, is_public)
                    VALUES (%s, %s, %s, %s)
                ''', (name, description, self.user_id, is_public))
            else:
                cursor.execute('''
                    INSERT INTO workout_templates (name, description, user_id, is_public)
                    VALUES (?, ?, ?, ?)
                ''', (name, description, self.user_id, is_public))
            template_id = cursor.lastrowid
            conn.commit()
            return template_id

    def get_user_templates(self):
        """Get all templates for the current user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if self.connection_manager.use_mysql:
                cursor.execute('''
                    SELECT wt.*, COUNT(wte.id) as exercise_count
                    FROM workout_templates wt
                    LEFT JOIN workout_template_exercises wte ON wt.id = wte.template_id
                    WHERE wt.user_id = %s
                    GROUP BY wt.id
                    ORDER BY wt.name
                ''', (self.user_id,))
            else:
                cursor.execute('''
                    SELECT wt.*, COUNT(wte.id) as exercise_count
                    FROM workout_templates wt
                    LEFT JOIN workout_template_exercises wte ON wt.id = wte.template_id
                    WHERE wt.user_id = ?
                    GROUP BY wt.id
                    ORDER BY wt.name
                ''', (self.user_id,))
            templates = cursor.fetchall()
            return templates

    def get_public_templates(self):
        """Get all public templates"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if self.connection_manager.use_mysql:
                cursor.execute('''
                    SELECT wt.*, COUNT(wte.id) as exercise_count
                    FROM workout_templates wt
                    LEFT JOIN workout_template_exercises wte ON wt.id = wte.template_id
                    WHERE wt.is_public = 1
                    GROUP BY wt.id
                    ORDER BY wt.name
                ''')
            else:
                cursor.execute('''
                    SELECT wt.*, COUNT(wte.id) as exercise_count
                    FROM workout_templates wt
                    LEFT JOIN workout_template_exercises wte ON wt.id = wte.template_id
                    WHERE wt.is_public = 1
                    GROUP BY wt.id
                    ORDER BY wt.name
                ''')
            templates = cursor.fetchall()
            return templates

    def get_template_details(self, template_id):
        """Get template details including all exercises"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Get template info
            if self.connection_manager.use_mysql:
                cursor.execute('''
                    SELECT * FROM workout_templates
                    WHERE id = %s AND (user_id = %s OR is_public = 1)
                ''', (template_id, self.user_id))
            else:
                cursor.execute('''
                    SELECT * FROM workout_templates
                    WHERE id = ? AND (user_id = ? OR is_public = 1)
                ''', (template_id, self.user_id))
            template = cursor.fetchone()

            if not template:
                return None, []

            # Get all exercises in this template
            if self.connection_manager.use_mysql:
                cursor.execute('''
                    SELECT wte.*, e.name, e.muscle_group
                    FROM workout_template_exercises wte
                    JOIN exercises e ON wte.exercise_id = e.id
                    WHERE wte.template_id = %s
                    ORDER BY wte.order_index
                ''', (template_id,))
            else:
                cursor.execute('''
                    SELECT wte.*, e.name, e.muscle_group
                    FROM workout_template_exercises wte
                    JOIN exercises e ON wte.exercise_id = e.id
                    WHERE wte.template_id = ?
                    ORDER BY wte.order_index
                ''', (template_id,))
            exercises = cursor.fetchall()

            return template, exercises

    def add_exercise_to_template(self, template_id, exercise_id, order_index, sets=3, target_reps=None, target_weight=None, rest_seconds=90, notes=None):
        """Add an exercise to a workout template"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Verify template belongs to user
            if self.connection_manager.use_mysql:
                cursor.execute('SELECT id FROM workout_templates WHERE id = %s AND user_id = %s', (template_id, self.user_id))
            else:
                cursor.execute('SELECT id FROM workout_templates WHERE id = ? AND user_id = ?', (template_id, self.user_id))

            if not cursor.fetchone():
                return False, "Template not found or unauthorized"

            try:
                if self.connection_manager.use_mysql:
                    cursor.execute('''
                        INSERT INTO workout_template_exercises
                        (template_id, exercise_id, order_index, sets, target_reps, target_weight, rest_seconds, notes)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (template_id, exercise_id, order_index, sets, target_reps, target_weight, rest_seconds, notes))
                else:
                    cursor.execute('''
                        INSERT INTO workout_template_exercises
                        (template_id, exercise_id, order_index, sets, target_reps, target_weight, rest_seconds, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (template_id, exercise_id, order_index, sets, target_reps, target_weight, rest_seconds, notes))
                conn.commit()
                return True, "Exercise added to template"
            except Exception as e:
                return False, "Order index already exists in template"

    def update_template_exercise(self, template_exercise_id, sets, target_reps, target_weight, rest_seconds, notes):
        """Update exercise details in a template"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Verify the template exercise belongs to user's template
            if self.connection_manager.use_mysql:
                cursor.execute('''
                    SELECT wte.id FROM workout_template_exercises wte
                    JOIN workout_templates wt ON wte.template_id = wt.id
                    WHERE wte.id = %s AND wt.user_id = %s
                ''', (template_exercise_id, self.user_id))
            else:
                cursor.execute('''
                    SELECT wte.id FROM workout_template_exercises wte
                    JOIN workout_templates wt ON wte.template_id = wt.id
                    WHERE wte.id = ? AND wt.user_id = ?
                ''', (template_exercise_id, self.user_id))

            if not cursor.fetchone():
                return False, "Template exercise not found or unauthorized"

            if self.connection_manager.use_mysql:
                cursor.execute('''
                    UPDATE workout_template_exercises
                    SET sets = %s, target_reps = %s, target_weight = %s, rest_seconds = %s, notes = %s
                    WHERE id = %s
                ''', (sets, target_reps, target_weight, rest_seconds, notes, template_exercise_id))
            else:
                cursor.execute('''
                    UPDATE workout_template_exercises
                    SET sets = ?, target_reps = ?, target_weight = ?, rest_seconds = ?, notes = ?
                    WHERE id = ?
                ''', (sets, target_reps, target_weight, rest_seconds, notes, template_exercise_id))
            conn.commit()
            return True, "Template exercise updated"

    def remove_exercise_from_template(self, template_exercise_id):
        """Remove an exercise from a template"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Verify the template exercise belongs to user's template
            if self.connection_manager.use_mysql:
                cursor.execute('''
                    SELECT wte.id FROM workout_template_exercises wte
                    JOIN workout_templates wt ON wte.template_id = wt.id
                    WHERE wte.id = %s AND wt.user_id = %s
                ''', (template_exercise_id, self.user_id))
            else:
                cursor.execute('''
                    SELECT wte.id FROM workout_template_exercises wte
                    JOIN workout_templates wt ON wte.template_id = wt.id
                    WHERE wte.id = ? AND wt.user_id = ?
                ''', (template_exercise_id, self.user_id))

            if not cursor.fetchone():
                return False, "Template exercise not found or unauthorized"

            if self.connection_manager.use_mysql:
                cursor.execute('DELETE FROM workout_template_exercises WHERE id = %s', (template_exercise_id,))
            else:
                cursor.execute('DELETE FROM workout_template_exercises WHERE id = ?', (template_exercise_id,))
            conn.commit()
            return True, "Exercise removed from template"

    def start_workout_from_template(self, template_id, notes=None):
        """Start a new workout session from a template"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Get template exercises
            if self.connection_manager.use_mysql:
                cursor.execute('''
                    SELECT exercise_id, sets, target_weight, target_reps
                    FROM workout_template_exercises
                    WHERE template_id = %s
                    ORDER BY order_index
                ''', (template_id,))
            else:
                cursor.execute('''
                    SELECT exercise_id, sets, target_weight, target_reps
                    FROM workout_template_exercises
                    WHERE template_id = ?
                    ORDER BY order_index
                ''', (template_id,))
            template_exercises = cursor.fetchall()

            if not template_exercises:
                return None, "Template has no exercises"

            # Create workout session with 'in_progress' status
            if self.connection_manager.use_mysql:
                cursor.execute('''
                    INSERT INTO workout_sessions (user_id, date, notes, template_id, status)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (self.user_id, datetime.now().date(), notes, template_id, 'in_progress'))
            else:
                cursor.execute('''
                    INSERT INTO workout_sessions (user_id, date, notes, template_id, status)
                    VALUES (?, ?, ?, ?, ?)
                ''', (self.user_id, datetime.now().date(), notes, template_id, 'in_progress'))
            session_id = cursor.lastrowid

            # Import progression service for historical analysis
            from models.services.progression_service import ProgressionService
            progression_service = ProgressionService()

            # Pre-populate sets based on historical performance analysis, not template defaults
            for exercise_id, num_sets, template_weight, template_reps in template_exercises:
                # Get last performance for this exercise
                last_performance = self.get_last_exercise_performance(exercise_id)

                # Get progression readiness to determine suggested weights/reps
                readiness = progression_service.check_progression_readiness(self.user_id, exercise_id)

                # Determine starting weight and reps based on analysis
                if last_performance:
                    # Use historical performance as starting point
                    suggested_weight = last_performance['max_weight']
                    suggested_reps = last_performance['max_reps']

                    # If ready for progression, use suggested progression values
                    if readiness.get('ready') and readiness.get('suggestion') == 'increase_weight':
                        suggested_weight = readiness.get('new_weight', suggested_weight)
                        suggested_reps = readiness.get('new_reps_target', suggested_reps)
                    elif readiness.get('current_avg_reps'):
                        # Use current average reps if available
                        suggested_reps = int(readiness['current_avg_reps'])
                else:
                    # Fallback to template values if no historical data
                    suggested_weight = template_weight or 0
                    suggested_reps = template_reps or 0

                # Create sets with analyzed values
                for set_num in range(1, num_sets + 1):
                    if self.connection_manager.use_mysql:
                        cursor.execute('''
                            INSERT INTO workout_sets (session_id, exercise_id, set_number, weight, reps)
                            VALUES (%s, %s, %s, %s, %s)
                        ''', (session_id, exercise_id, set_num, suggested_weight, suggested_reps))
                    else:
                        cursor.execute('''
                            INSERT INTO workout_sets (session_id, exercise_id, set_number, weight, reps)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (session_id, exercise_id, set_num, suggested_weight, suggested_reps))

            conn.commit()
            return session_id, "Workout started from template with progression analysis"

    def delete_template(self, template_id):
        """Delete a workout template"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Verify template belongs to user
            if self.connection_manager.use_mysql:
                cursor.execute('SELECT id FROM workout_templates WHERE id = %s AND user_id = %s', (template_id, self.user_id))
            else:
                cursor.execute('SELECT id FROM workout_templates WHERE id = ? AND user_id = ?', (template_id, self.user_id))

            if not cursor.fetchone():
                return False, "Template not found or unauthorized"

            # Delete template (cascade will delete template exercises)
            if self.connection_manager.use_mysql:
                cursor.execute('DELETE FROM workout_templates WHERE id = %s', (template_id,))
            else:
                cursor.execute('DELETE FROM workout_templates WHERE id = ?', (template_id,))
            conn.commit()
            return True, "Template deleted successfully"

    def update_template(self, template_id, name, description, is_public):
        """Update template details"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if self.connection_manager.use_mysql:
                cursor.execute('''
                    UPDATE workout_templates
                    SET name = %s, description = %s, is_public = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND user_id = %s
                ''', (name, description, is_public, template_id, self.user_id))
            else:
                cursor.execute('''
                    UPDATE workout_templates
                    SET name = ?, description = ?, is_public = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND user_id = ?
                ''', (name, description, is_public, template_id, self.user_id))

            if cursor.rowcount > 0:
                conn.commit()
                return True, "Template updated successfully"
            else:
                return False, "Template not found or unauthorized"

    # Workout Completion Methods

    def complete_workout(self, workout_id):
        """Mark a workout as completed"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if self.connection_manager.use_mysql:
                cursor.execute('''
                    UPDATE workout_sessions
                    SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND user_id = %s AND status = 'in_progress'
                ''', (workout_id, self.user_id))
            else:
                cursor.execute('''
                    UPDATE workout_sessions
                    SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND user_id = ? AND status = 'in_progress'
                ''', (workout_id, self.user_id))

            if cursor.rowcount > 0:
                # Get all exercises in this workout before committing
                if self.connection_manager.use_mysql:
                    cursor.execute('''
                        SELECT DISTINCT exercise_id
                        FROM workout_sets
                        WHERE session_id = %s
                    ''', (workout_id,))
                else:
                    cursor.execute('''
                        SELECT DISTINCT exercise_id
                        FROM workout_sets
                        WHERE session_id = ?
                    ''', (workout_id,))

                exercises = cursor.fetchall()

                # Commit the workout completion first
                conn.commit()

                # Calculate volume metrics for each exercise in the workout
                # This now happens after the connection is closed to avoid locks
                from models.services.advanced_progression_service import AdvancedProgressionService
                adv_service = AdvancedProgressionService(self.db_path)

                # Calculate volume for each exercise
                for (exercise_id,) in exercises:
                    adv_service.calculate_volume_metrics(workout_id, exercise_id)

                return True, "Workout completed successfully"
            else:
                return False, "Workout not found, already completed, or unauthorized"

    def abandon_workout(self, workout_id):
        """Mark a workout as abandoned"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if self.connection_manager.use_mysql:
                cursor.execute('''
                    UPDATE workout_sessions
                    SET status = 'abandoned', completed_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND user_id = %s AND status = 'in_progress'
                ''', (workout_id, self.user_id))
            else:
                cursor.execute('''
                    UPDATE workout_sessions
                    SET status = 'abandoned', completed_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND user_id = ? AND status = 'in_progress'
                ''', (workout_id, self.user_id))

            if cursor.rowcount > 0:
                conn.commit()
                return True, "Workout abandoned"
            else:
                return False, "Workout not found, already completed, or unauthorized"

    def get_workout_status(self, workout_id):
        """Get the status of a workout"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if self.connection_manager.use_mysql:
                cursor.execute('''
                    SELECT status, completed_at FROM workout_sessions
                    WHERE id = %s AND user_id = %s
                ''', (workout_id, self.user_id))
            else:
                cursor.execute('''
                    SELECT status, completed_at FROM workout_sessions
                    WHERE id = ? AND user_id = ?
                ''', (workout_id, self.user_id))

            result = cursor.fetchone()

            if result:
                return result[0], result[1]
            return None, None

    def get_workout_summary(self, workout_id):
        """Get summary statistics for a completed workout"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Get workout info
            if self.connection_manager.use_mysql:
                cursor.execute('''
                    SELECT date, created_at, completed_at, status
                    FROM workout_sessions
                    WHERE id = %s AND user_id = %s
                ''', (workout_id, self.user_id))
            else:
                cursor.execute('''
                    SELECT date, created_at, completed_at, status
                    FROM workout_sessions
                    WHERE id = ? AND user_id = ?
                ''', (workout_id, self.user_id))

            workout_info = cursor.fetchone()
            if not workout_info:
                return None

            # Calculate duration if completed
            duration = None
            if workout_info[2]:  # completed_at exists
                created = datetime.fromisoformat(workout_info[1])
                completed = datetime.fromisoformat(workout_info[2])
                duration = int((completed - created).total_seconds() / 60)  # minutes

            # Get statistics
            if self.connection_manager.use_mysql:
                cursor.execute('''
                    SELECT
                        COUNT(DISTINCT exercise_id) as exercise_count,
                        COUNT(*) as total_sets,
                        SUM(weight * reps) as total_volume,
                        SUM(reps) as total_reps
                    FROM workout_sets
                    WHERE session_id = %s
                ''', (workout_id,))
            else:
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
        with self.get_connection() as conn:
            cursor = conn.cursor()

            try:
                # Verify workout belongs to user
                if self.connection_manager.use_mysql:
                    cursor.execute('''
                        SELECT id FROM workout_sessions
                        WHERE id = %s AND user_id = %s
                    ''', (workout_id, self.user_id))
                else:
                    cursor.execute('''
                        SELECT id FROM workout_sessions
                        WHERE id = ? AND user_id = ?
                    ''', (workout_id, self.user_id))

                if not cursor.fetchone():
                    return None, "Workout not found or unauthorized"

                # Get all exercises from the workout
                if self.connection_manager.use_mysql:
                    cursor.execute('''
                        SELECT DISTINCT ws.exercise_id,
                               COUNT(*) as num_sets,
                               AVG(ws.weight) as avg_weight,
                               AVG(ws.reps) as avg_reps,
                               MIN(ws.set_number) as min_set_num
                        FROM workout_sets ws
                        WHERE ws.session_id = %s
                        GROUP BY ws.exercise_id
                        ORDER BY MIN(ws.id)
                    ''', (workout_id,))
                else:
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
                    return None, "No exercises found in workout"

                # Create the template
                if self.connection_manager.use_mysql:
                    cursor.execute('''
                        INSERT INTO workout_templates (name, description, user_id, is_public)
                        VALUES (%s, %s, %s, %s)
                    ''', (name, description, self.user_id, is_public))
                else:
                    cursor.execute('''
                        INSERT INTO workout_templates (name, description, user_id, is_public)
                        VALUES (?, ?, ?, ?)
                    ''', (name, description, self.user_id, is_public))

                template_id = cursor.lastrowid

                # Add exercises to template
                for order, (exercise_id, num_sets, avg_weight, avg_reps, _) in enumerate(exercises, 1):
                    if self.connection_manager.use_mysql:
                        cursor.execute('''
                            INSERT INTO workout_template_exercises
                            (template_id, exercise_id, order_index, sets, target_reps, target_weight, rest_seconds)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ''', (template_id, exercise_id, order, num_sets,
                              int(round(avg_reps)), round(avg_weight, 1), 90))
                    else:
                        cursor.execute('''
                            INSERT INTO workout_template_exercises
                            (template_id, exercise_id, order_index, sets, target_reps, target_weight, rest_seconds)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (template_id, exercise_id, order, num_sets,
                              int(round(avg_reps)), round(avg_weight, 1), 90))

                conn.commit()
                return template_id, "Template created successfully"

            except Exception as e:
                conn.rollback()
                return None, f"Error creating template: {str(e)}"

    def get_last_exercise_performance(self, exercise_id):
        """Get the last performance for a specific exercise"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if self.connection_manager.use_mysql:
                cursor.execute('''
                    SELECT
                        MAX(ws.weight) as max_weight,
                        MAX(ws.reps) as max_reps,
                        wss.date
                    FROM workout_sets ws
                    JOIN workout_sessions wss ON ws.session_id = wss.id
                    WHERE ws.exercise_id = %s AND wss.user_id = %s
                    GROUP BY wss.id
                    ORDER BY wss.date DESC, wss.id DESC
                    LIMIT 1
                ''', (exercise_id, self.user_id))
            else:
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

            if result:
                return {
                    'max_weight': result[0],
                    'max_reps': result[1],
                    'workout_date': result[2]
                }
            return None
