"""
Progression Repository - handles all progression-related database queries
"""

from datetime import datetime
from typing import Dict, Optional
import logging
from ..base import BaseProgressionService

logger = logging.getLogger(__name__)


class ProgressionRepository(BaseProgressionService):
    """Repository for progression-related database operations"""

    def get_user_preferences(self, user_id: int) -> Optional[Dict]:
        """Get user's gym preferences"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT progression_strategy, min_reps_target, max_reps_target,
                           weight_increment_upper, weight_increment_lower,
                           rest_timer_enabled, progression_notification_enabled,
                           pyramid_preference
                    FROM user_gym_preferences
                    WHERE user_id = %s
                ''', (user_id,))

                row = cursor.fetchone()
                if row:
                    return {
                        'progression_strategy': row[0] or 'reps_first',
                        'min_reps_target': row[1] or 10,
                        'max_reps_target': row[2] or 15,
                        'weight_increment_upper': row[3] or 2.5,
                        'weight_increment_lower': row[4] or 5.0,
                        'rest_timer_enabled': bool(row[5]) if row[5] is not None else True,
                        'progression_notification_enabled': bool(row[6]) if row[6] is not None else True,
                        'pyramid_preference': row[7] or 'auto_detect'
                    }
                return None

        except Exception as e:
            logger.error(f"Error fetching user preferences: {e}")
            return None

    def update_user_preferences(self, user_id: int, preferences: Dict) -> bool:
        """Update user's gym preferences"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    INSERT INTO user_gym_preferences
                    (user_id, progression_strategy, min_reps_target, max_reps_target,
                     weight_increment_upper, weight_increment_lower,
                     rest_timer_enabled, progression_notification_enabled,
                     pyramid_preference, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON DUPLICATE KEY UPDATE
                        progression_strategy = VALUES(progression_strategy),
                        min_reps_target = VALUES(min_reps_target),
                        max_reps_target = VALUES(max_reps_target),
                        weight_increment_upper = VALUES(weight_increment_upper),
                        weight_increment_lower = VALUES(weight_increment_lower),
                        rest_timer_enabled = VALUES(rest_timer_enabled),
                        progression_notification_enabled = VALUES(progression_notification_enabled),
                        pyramid_preference = VALUES(pyramid_preference),
                        updated_at = CURRENT_TIMESTAMP
                ''', (
                    user_id,
                    preferences.get('progression_strategy', 'reps_first'),
                    preferences.get('min_reps_target', 10),
                    preferences.get('max_reps_target', 15),
                    preferences.get('weight_increment_upper', 2.5),
                    preferences.get('weight_increment_lower', 5.0),
                    preferences.get('rest_timer_enabled', True),
                    preferences.get('progression_notification_enabled', True),
                    preferences.get('pyramid_preference', 'auto_detect')
                ))

                conn.commit()
                return True

        except Exception as e:
            logger.error(f"Error updating preferences: {e}")
            return False

    def record_progression(self, user_id: int, exercise_id: int,
                          old_weight: float, new_weight: float,
                          progression_type: str = 'weight_increase',
                          notes: str = '') -> bool:
        """Record a progression event"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    INSERT INTO progression_history
                    (user_id, exercise_id, progression_date, old_weight, new_weight,
                     progression_type, notes)
                    VALUES (%s, %s, CURDATE(), %s, %s, %s, %s)
                ''', (user_id, exercise_id, old_weight, new_weight,
                      progression_type, notes))

                conn.commit()
                logger.info(f"Recorded progression for user {user_id}, exercise {exercise_id}")
                return True

        except Exception as e:
            logger.error(f"Error recording progression: {e}")
            return False

    def record_set_progression(self, user_id: int, exercise_id: int, set_number: int,
                             old_weight: float, new_weight: float, old_reps: int,
                             new_reps: int, progression_type: str, notes: str = '') -> bool:
        """Record a set-specific progression event"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    INSERT INTO set_progression_history
                    (user_id, exercise_id, set_number, progression_date,
                     old_weight, new_weight, old_reps, new_reps,
                     progression_type, notes)
                    VALUES (%s, %s, %s, CURDATE(), %s, %s, %s, %s, %s, %s)
                ''', (user_id, exercise_id, set_number, old_weight, new_weight,
                      old_reps, new_reps, progression_type, notes))

                conn.commit()
                return True

        except Exception as e:
            logger.error(f"Error recording set progression: {e}")
            return False

    def get_last_progression_date(self, user_id: int, exercise_id: int) -> Optional[datetime]:
        """Get the date of the last progression for an exercise"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT MAX(progression_date)
                    FROM progression_history
                    WHERE user_id = %s AND exercise_id = %s
                ''', (user_id, exercise_id))

                result = cursor.fetchone()
                if result and result[0]:
                    return result[0]
                return None

        except Exception as e:
            logger.error(f"Error getting last progression date: {e}")
            return None

    def calculate_and_store_volume_metrics(self, workout_id: int, exercise_id: int) -> Dict:
        """Calculate and store volume metrics for a workout"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Get all sets for this exercise in this workout
                cursor.execute('''
                    SELECT weight, reps
                    FROM workout_sets
                    WHERE session_id = %s AND exercise_id = %s
                ''', (workout_id, exercise_id))

                sets = cursor.fetchall()
                if not sets:
                    return {'error': 'No sets found'}

                # Calculate metrics
                total_volume = sum(weight * reps for weight, reps in sets)
                total_reps = sum(reps for _, reps in sets)
                total_sets = len(sets)
                avg_intensity = sum(weight for weight, _ in sets) / len(sets)

                # Store in database
                cursor.execute('''
                    INSERT INTO workout_volume_tracking
                    (workout_id, exercise_id, total_volume, total_reps, total_sets, avg_intensity)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        total_volume = VALUES(total_volume),
                        total_reps = VALUES(total_reps),
                        total_sets = VALUES(total_sets),
                        avg_intensity = VALUES(avg_intensity)
                ''', (workout_id, exercise_id, total_volume, total_reps, total_sets, avg_intensity))

                conn.commit()

                return {
                    'total_volume': total_volume,
                    'total_reps': total_reps,
                    'total_sets': total_sets,
                    'avg_intensity': round(avg_intensity, 1)
                }

        except Exception as e:
            logger.error(f"Error calculating volume metrics: {e}")
            return {'error': str(e)}
