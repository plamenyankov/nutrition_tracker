"""
Progressive Overload Service for Gym Tracker
Handles progression detection, suggestions, and tracking
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import statistics
import os
import logging
from .progression_config import get_config, ProgressionConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProgressionServiceError(Exception):
    """Custom exception for progression service errors"""
    pass

class ProgressionService:
    def __init__(self, db_path=None, config: ProgressionConfig = None):
        if db_path is None:
            db_path = os.getenv('DATABASE_PATH', 'database.db')
        self.db_path = db_path

        # Use provided config or get global config
        self.config = config or get_config()

    def _get_connection(self):
        """Get a database connection with WAL mode enabled and error handling"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")  # Enable foreign key constraints
            return conn
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {e}")
            raise ProgressionServiceError(f"Failed to connect to database: {e}")

    def _validate_user_data(self, user_id: int) -> bool:
        """Validate that user has sufficient data for progression analysis"""
        if not user_id or user_id <= 0:
            return False

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Check if user has any completed workouts
            cursor.execute('''
                SELECT COUNT(*) FROM workout_sessions
                WHERE user_id = ? AND status = 'completed'
            ''', (user_id,))

            workout_count = cursor.fetchone()[0]
            conn.close()

            return workout_count >= self.config.pattern_detection.min_workouts

        except sqlite3.Error as e:
            logger.error(f"Error validating user data: {e}")
            return False

    def _cleanup_orphaned_records(self, user_id: int) -> Dict:
        """Clean up orphaned workout_sets without valid sessions"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Find orphaned workout_sets
            cursor.execute('''
                SELECT COUNT(*) FROM workout_sets ws
                WHERE NOT EXISTS (
                    SELECT 1 FROM workout_sessions wss
                    WHERE wss.id = ws.session_id AND wss.user_id = ?
                )
            ''', (user_id,))

            orphaned_count = cursor.fetchone()[0]

            if orphaned_count > 0:
                # Delete orphaned records
                cursor.execute('''
                    DELETE FROM workout_sets
                    WHERE NOT EXISTS (
                        SELECT 1 FROM workout_sessions wss
                        WHERE wss.id = workout_sets.session_id AND wss.user_id = ?
                    )
                ''', (user_id,))

                conn.commit()
                logger.info(f"Cleaned up {orphaned_count} orphaned workout_sets for user {user_id}")

            conn.close()
            return {'cleaned_records': orphaned_count}

        except sqlite3.Error as e:
            logger.error(f"Error cleaning orphaned records: {e}")
            return {'error': str(e), 'cleaned_records': 0}

    def _validate_progression_data(self, old_weight: float, new_weight: float) -> bool:
        """Validate that progression data makes sense (no weight decreases marked as progressions)"""
        if old_weight is None or new_weight is None:
            return False

        if old_weight <= 0 or new_weight <= 0:
            return False

        # Ensure new weight is actually higher (progression)
        if new_weight <= old_weight:
            logger.warning(f"Invalid progression: new weight {new_weight} not greater than old weight {old_weight}")
            return False

        # Check for unrealistic jumps using config
        max_jump = 1 + (self.config.progression_thresholds.max_weight_jump_percentage / 100)
        if new_weight > old_weight * max_jump:
            logger.warning(f"Suspicious progression jump: {old_weight}kg to {new_weight}kg (max allowed: {max_jump:.1f}x)")
            return False

        return True

    def get_user_preferences(self, user_id: int) -> Dict:
        """Get user's gym preferences with comprehensive error handling"""
        if not self._validate_user_data(user_id):
            logger.warning(f"User {user_id} has insufficient data, returning defaults")
            return self._get_default_preferences()

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT progression_strategy, min_reps_target, max_reps_target,
                       weight_increment_upper, weight_increment_lower,
                       rest_timer_enabled, progression_notification_enabled,
                       progression_priority_1, progression_priority_2,
                       progression_priority_3, progression_priority_4,
                       progression_priority_5, pyramid_preference
                FROM user_gym_preferences
                WHERE user_id = ?
            ''', (user_id,))

            row = cursor.fetchone()
            conn.close()

            if row:
                return {
                    'progression_strategy': row[0] or 'reps_first',
                    'min_reps_target': row[1] or 10,
                    'max_reps_target': row[2] or 15,
                    'weight_increment_upper': row[3] or 2.5,
                    'weight_increment_lower': row[4] or 5.0,
                    'rest_timer_enabled': bool(row[5]) if row[5] is not None else True,
                    'progression_notification_enabled': bool(row[6]) if row[6] is not None else True,
                    'progression_priority_1': row[7] or 'reps',
                    'progression_priority_2': row[8] or 'weight',
                    'progression_priority_3': row[9] or 'volume',
                    'progression_priority_4': row[10] or 'sets',
                    'progression_priority_5': row[11] or 'exercises',
                    'pyramid_preference': row[12] or 'auto_detect'
                }
            else:
                return self._get_default_preferences()

        except sqlite3.Error as e:
            logger.error(f"Error fetching user preferences: {e}")
            return self._get_default_preferences()

    def _get_default_preferences(self) -> Dict:
        """Return default preferences when user data is unavailable"""
        defaults = self.config.get_user_preference_defaults()
        # Add progression priorities that aren't in the config dataclass
        defaults.update({
            'progression_priority_1': 'reps',
            'progression_priority_2': 'weight',
            'progression_priority_3': 'volume',
            'progression_priority_4': 'sets',
            'progression_priority_5': 'exercises'
        })
        return defaults

    def update_user_preferences(self, user_id: int, preferences: Dict) -> bool:
        """Update user's gym preferences"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT OR REPLACE INTO user_gym_preferences
                (user_id, progression_strategy, min_reps_target, max_reps_target,
                 weight_increment_upper, weight_increment_lower,
                 rest_timer_enabled, progression_notification_enabled,
                 progression_priority_1, progression_priority_2,
                 progression_priority_3, progression_priority_4,
                 progression_priority_5, pyramid_preference,
                 updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                user_id,
                preferences.get('progression_strategy', 'reps_first'),
                preferences.get('min_reps_target', 10),
                preferences.get('max_reps_target', 15),
                preferences.get('weight_increment_upper', 2.5),
                preferences.get('weight_increment_lower', 5.0),
                preferences.get('rest_timer_enabled', True),
                preferences.get('progression_notification_enabled', True),
                preferences.get('progression_priority_1', 'reps'),
                preferences.get('progression_priority_2', 'weight'),
                preferences.get('progression_priority_3', 'volume'),
                preferences.get('progression_priority_4', 'sets'),
                preferences.get('progression_priority_5', 'exercises'),
                preferences.get('pyramid_preference', 'auto_detect')
            ))

            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error updating preferences: {e}")
            return False
        finally:
            conn.close()

    def get_exercise_performance_history(self, user_id: int, exercise_id: int,
                                       limit: int = 5) -> List[Dict]:
        """Get last N performances for an exercise with error handling"""
        if not self._validate_user_data(user_id):
            return []

        if exercise_id <= 0:
            logger.error(f"Invalid exercise_id: {exercise_id}")
            return []

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Use COALESCE for null handling as per improvement document
            cursor.execute('''
                SELECT ws.id, ws.date,
                       COALESCE(wset.weight, 0) as weight,
                       COALESCE(wset.reps, 0) as reps,
                       wset.set_number,
                       COALESCE(wset.rpe, 0) as rpe,
                       COALESCE(wset.form_quality, 0) as form_quality
                FROM workout_sessions ws
                JOIN workout_sets wset ON ws.id = wset.session_id
                WHERE ws.user_id = ? AND wset.exercise_id = ?
                      AND ws.status = 'completed'
                      AND wset.weight > 0 AND wset.reps > 0  -- Filter out invalid data
                ORDER BY ws.date DESC, wset.set_number
                LIMIT ?
            ''', (user_id, exercise_id, limit * 10))

            rows = cursor.fetchall()
            conn.close()

            if not rows:
                logger.info(f"No performance history found for user {user_id}, exercise {exercise_id}")
                return []

            # Group by workout session
            workouts = {}
            for row in rows:
                workout_id = row[0]
                if workout_id not in workouts:
                    workouts[workout_id] = {
                        'workout_id': workout_id,
                        'date': row[1],
                        'sets': []
                    }

                workouts[workout_id]['sets'].append({
                    'weight': row[2],
                    'reps': row[3],
                    'set_number': row[4],
                    'rpe': row[5],
                    'form_quality': row[6]
                })

            # Return as list, limited to requested number
            return list(workouts.values())[:limit]

        except sqlite3.Error as e:
            logger.error(f"Error fetching exercise performance history: {e}")
            return []

    def check_progression_readiness(self, user_id: int, exercise_id: int) -> Dict:
        """Check if user is ready to progress on an exercise with comprehensive error handling"""
        # Clean up any orphaned data first
        cleanup_result = self._cleanup_orphaned_records(user_id)

        if not self._validate_user_data(user_id):
            return {
                'ready': False,
                'reason': 'New user - complete at least 3 workouts to see progression suggestions',
                'suggestion': 'focus_on_consistency',
                'confidence': 0.0,
                'user_state': 'new_user'
            }

        try:
            prefs = self.get_user_preferences(user_id)
            history = self.get_exercise_performance_history(user_id, exercise_id, limit=5)

            if len(history) < 2:
                return {
                    'ready': False,
                    'reason': 'Need at least 2 completed workouts for this exercise',
                    'suggestion': 'complete_more_workouts',
                    'confidence': 0.0,
                    'workouts_needed': 2 - len(history),
                    'user_state': 'minimal_data'
                }

            # Get exercise info to determine if upper or lower body
            exercise_info = self._get_exercise_info(exercise_id)
            if not exercise_info:
                return {
                    'ready': False,
                    'reason': 'Exercise information not found',
                    'suggestion': 'check_exercise_data',
                    'confidence': 0.0,
                    'user_state': 'data_error'
                }

            is_upper_body = self._is_upper_body_exercise(exercise_info)

            if prefs['progression_strategy'] == 'reps_first':
                return self._check_reps_first_progression(history, prefs, is_upper_body)
            elif prefs['progression_strategy'] == 'weight_first':
                return self._check_weight_first_progression(history, prefs, is_upper_body)
            else:
                return self._check_hybrid_progression(history, prefs, is_upper_body)

        except Exception as e:
            logger.error(f"Error checking progression readiness: {e}")
            return {
                'ready': False,
                'reason': 'System error - please try again',
                'suggestion': 'retry_later',
                'confidence': 0.0,
                'error': str(e),
                'user_state': 'system_error'
            }

    def _check_reps_first_progression(self, history: List[Dict], prefs: Dict,
                                    is_upper_body: bool) -> Dict:
        """Check progression for reps-first strategy"""
        max_reps_target = prefs['max_reps_target']
        min_reps_target = prefs['min_reps_target']

        # Check last 2 workouts
        ready_count = 0
        current_weight = None
        avg_reps_list = []

        for workout in history[:2]:
            if not workout['sets']:
                continue

            # Get average reps and weight for this workout
            weights = [s['weight'] for s in workout['sets']]
            reps = [s['reps'] for s in workout['sets']]

            if not weights or not reps:
                continue

            avg_weight = statistics.mean(weights)
            avg_reps = statistics.mean(reps)
            avg_reps_list.append(avg_reps)

            if current_weight is None:
                current_weight = avg_weight

            # Check if all sets hit max reps target
            if all(s['reps'] >= max_reps_target for s in workout['sets']):
                ready_count += 1

        if ready_count >= 2:
            # Ready to increase weight
            weight_increment = (prefs['weight_increment_upper'] if is_upper_body
                              else prefs['weight_increment_lower'])

            return {
                'ready': True,
                'suggestion': 'increase_weight',
                'current_weight': current_weight,
                'new_weight': current_weight + weight_increment,
                'new_reps_target': min_reps_target,
                'reason': f'Consistently hit {max_reps_target} reps for 2 workouts'
            }
        else:
            # Calculate how close they are
            if avg_reps_list:
                current_avg_reps = statistics.mean(avg_reps_list)
                reps_to_go = max_reps_target - current_avg_reps

                return {
                    'ready': False,
                    'suggestion': 'increase_reps',
                    'current_avg_reps': round(current_avg_reps, 1),
                    'target_reps': max_reps_target,
                    'reps_to_go': round(reps_to_go, 1),
                    'reason': f'Average {current_avg_reps:.1f} reps, need {max_reps_target}'
                }
            else:
                return {
                    'ready': False,
                    'reason': 'Insufficient data',
                    'suggestion': 'Continue current program'
                }

    def _is_upper_body_exercise(self, exercise_info: Dict) -> bool:
        """Determine if exercise is upper body based on muscle groups"""
        if not exercise_info:
            return True  # Default to upper body (smaller increments)

        lower_body_keywords = ['leg', 'glute', 'quad', 'hamstring', 'calf', 'squat', 'deadlift']
        name = exercise_info.get('name', '').lower()
        muscle_group = exercise_info.get('muscle_group', '').lower()

        for keyword in lower_body_keywords:
            if keyword in name or keyword in muscle_group:
                return False

        return True

    def _get_exercise_info(self, exercise_id: int) -> Dict:
        """Get exercise information"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT name, muscle_group
            FROM exercises
            WHERE id = ?
        ''', (exercise_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'name': row[0],
                'muscle_group': row[1],
                'equipment': None  # Equipment column doesn't exist in production
            }
        return {}

    def record_progression(self, user_id: int, exercise_id: int,
                          old_weight: float, new_weight: float,
                          progression_type: str = 'weight_increase',
                          notes: str = '') -> bool:
        """Record a progression event with comprehensive validation"""
        # Validate input data
        if not self._validate_user_data(user_id):
            logger.error(f"Cannot record progression for user {user_id}: insufficient data")
            return False

        if exercise_id <= 0:
            logger.error(f"Invalid exercise_id: {exercise_id}")
            return False

        if not self._validate_progression_data(old_weight, new_weight):
            logger.error(f"Invalid progression data: {old_weight}kg -> {new_weight}kg")
            return False

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Check if exercise exists
            cursor.execute('SELECT id FROM exercises WHERE id = ?', (exercise_id,))
            if not cursor.fetchone():
                logger.error(f"Exercise {exercise_id} does not exist")
                conn.close()
                return False

            cursor.execute('''
                INSERT INTO progression_history
                (user_id, exercise_id, progression_date, old_weight, new_weight,
                 progression_type, notes)
                VALUES (?, ?, DATE('now'), ?, ?, ?, ?)
            ''', (user_id, exercise_id, old_weight, new_weight,
                  progression_type, notes))

            conn.commit()
            logger.info(f"Recorded progression for user {user_id}, exercise {exercise_id}: {old_weight}kg -> {new_weight}kg")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error recording progression: {e}")
            return False
        finally:
            conn.close()

    def get_progression_suggestions(self, user_id: int, workout_id: Optional[int] = None) -> List[Dict]:
        """Get progression suggestions for user's exercises with comprehensive error handling"""
        if not self._validate_user_data(user_id):
            return [{
                'exercise_id': None,
                'exercise_name': 'No Data Available',
                'muscle_group': '',
                'ready': False,
                'reason': 'Complete at least 3 workouts to see progression suggestions',
                'suggestion': 'focus_on_consistency',
                'user_state': 'new_user'
            }]

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Get exercises from current workout or recent workouts
            if workout_id:
                # Validate workout belongs to user
                cursor.execute('''
                    SELECT user_id FROM workout_sessions WHERE id = ?
                ''', (workout_id,))
                workout_owner = cursor.fetchone()

                if not workout_owner or workout_owner[0] != user_id:
                    logger.error(f"Workout {workout_id} does not belong to user {user_id}")
                    conn.close()
                    return []

                cursor.execute('''
                    SELECT DISTINCT exercise_id
                    FROM workout_sets
                    WHERE session_id = ? AND exercise_id > 0
                ''', (workout_id,))
            else:
                # Get exercises from last 5 workouts
                cursor.execute('''
                    SELECT DISTINCT wset.exercise_id
                    FROM workout_sessions ws
                    JOIN workout_sets wset ON ws.id = wset.session_id
                    WHERE ws.user_id = ? AND ws.status = 'completed'
                          AND wset.exercise_id > 0
                    ORDER BY ws.date DESC
                    LIMIT 50
                ''', (user_id,))

            exercise_ids = [row[0] for row in cursor.fetchall()]
            conn.close()

            if not exercise_ids:
                return [{
                    'exercise_id': None,
                    'exercise_name': 'No Exercises Found',
                    'muscle_group': '',
                    'ready': False,
                    'reason': 'No exercise data available',
                    'suggestion': 'complete_workouts',
                    'user_state': 'no_exercises'
                }]

            # Check progression for each exercise
            suggestions = []
            for exercise_id in set(exercise_ids):  # Remove duplicates
                try:
                    readiness = self.check_progression_readiness(user_id, exercise_id)
                    exercise_info = self._get_exercise_info(exercise_id)

                    suggestions.append({
                        'exercise_id': exercise_id,
                        'exercise_name': exercise_info.get('name', 'Unknown Exercise'),
                        'muscle_group': exercise_info.get('muscle_group', 'Unknown'),
                        **readiness
                    })
                except Exception as e:
                    logger.error(f"Error processing exercise {exercise_id}: {e}")
                    # Continue with other exercises

            # Sort by readiness (ready first) and exercise name
            suggestions.sort(key=lambda x: (not x.get('ready', False), x.get('exercise_name', '')))

            return suggestions if suggestions else [{
                'exercise_id': None,
                'exercise_name': 'Processing Error',
                'muscle_group': '',
                'ready': False,
                'reason': 'Error processing exercise data',
                'suggestion': 'retry_later',
                'user_state': 'processing_error'
            }]

        except sqlite3.Error as e:
            logger.error(f"Database error in get_progression_suggestions: {e}")
            return [{
                'exercise_id': None,
                'exercise_name': 'Database Error',
                'muscle_group': '',
                'ready': False,
                'reason': 'Database connection error',
                'suggestion': 'retry_later',
                'user_state': 'database_error'
            }]

    def get_exercise_trend(self, user_id: int, exercise_id: int, days: int = 30) -> Dict:
        """Get exercise performance trend over time"""
        conn = self._get_connection()
        cursor = conn.cursor()

        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        cursor.execute('''
            SELECT ws.date, AVG(wset.weight) as avg_weight,
                   AVG(wset.reps) as avg_reps, COUNT(wset.id) as total_sets
            FROM workout_sessions ws
            JOIN workout_sets wset ON ws.id = wset.session_id
            WHERE ws.user_id = ? AND wset.exercise_id = ?
                  AND ws.date >= ? AND ws.status = 'completed'
            GROUP BY ws.date
            ORDER BY ws.date
        ''', (user_id, exercise_id, start_date))

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return {'trend': 'no_data', 'data_points': []}

        data_points = []
        for row in rows:
            data_points.append({
                'date': row[0],
                'avg_weight': round(row[1], 1),
                'avg_reps': round(row[2], 1),
                'total_sets': row[3]
            })

        # Calculate trend
        if len(data_points) >= 2:
            first_weight = data_points[0]['avg_weight']
            last_weight = data_points[-1]['avg_weight']
            weight_change = ((last_weight - first_weight) / first_weight) * 100

            if weight_change > 5:
                trend = 'improving'
            elif weight_change < -5:
                trend = 'declining'
            else:
                trend = 'stable'
        else:
            trend = 'insufficient_data'

        return {
            'trend': trend,
            'data_points': data_points,
            'days_analyzed': days
        }

    def _check_weight_first_progression(self, history: List[Dict], prefs: Dict,
                                      is_upper_body: bool) -> Dict:
        """Check progression for weight-first strategy"""
        # Implementation for weight-first strategy
        # This would focus on increasing weight when form is perfect
        # and RPE is low enough
        pass

    def _check_hybrid_progression(self, history: List[Dict], prefs: Dict,
                                is_upper_body: bool) -> Dict:
        """Check progression for hybrid strategy"""
        # Implementation for hybrid strategy
        # This would alternate between weight and rep increases
        pass
