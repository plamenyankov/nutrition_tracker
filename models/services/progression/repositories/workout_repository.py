"""
Workout Repository - handles all workout-related database queries
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging
from ..base import BaseProgressionService

logger = logging.getLogger(__name__)


class WorkoutRepository(BaseProgressionService):
    """Repository for workout-related database operations"""

    def get_exercise_info(self, exercise_id: int) -> Optional[Dict]:
        """Get exercise information"""
        if not self.validate_exercise_id(exercise_id):
            return None

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, name, muscle_group
                    FROM exercises
                    WHERE id = %s
                ''', (exercise_id,))

                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'name': row[1],
                        'muscle_group': row[2]
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting exercise info: {e}")
            return None

    def get_set_history(self, user_id: int, exercise_id: int, set_number: int, limit: int = 5) -> List[Dict]:
        """Get history for a specific set number"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT ws.date, wset.weight, wset.reps, wset.rpe, wset.form_quality
                    FROM workout_sets wset
                    JOIN workout_sessions ws ON wset.session_id = ws.id
                    WHERE ws.user_id = %s AND wset.exercise_id = %s AND wset.set_number = %s
                          AND ws.status = 'completed'
                    ORDER BY ws.date DESC
                    LIMIT %s
                ''', (user_id, exercise_id, set_number, limit))

                rows = cursor.fetchall()
                return [{
                    'date': row[0],
                    'weight': row[1],
                    'reps': row[2],
                    'rpe': row[3],
                    'form_quality': row[4]
                } for row in rows]
        except Exception as e:
            logger.error(f"Error getting set history: {e}")
            return []

    def get_recent_workouts(self, user_id: int, exercise_id: int, days: int = 30, limit: Optional[int] = None) -> List[Dict]:
        """Get recent workouts for an exercise"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                query = '''
                    SELECT ws.id, ws.date, wset.set_number, wset.weight, wset.reps,
                           wset.rpe, wset.form_quality
                    FROM workout_sessions ws
                    JOIN workout_sets wset ON ws.id = wset.session_id
                    WHERE ws.user_id = %s AND wset.exercise_id = %s
                          AND ws.date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                          AND ws.status = 'completed'
                    ORDER BY ws.date DESC, wset.set_number
                '''

                params = [user_id, exercise_id, days]
                if limit:
                    query += ' LIMIT %s'
                    params.append(limit)

                cursor.execute(query, params)
                rows = cursor.fetchall()

                # Group by workout session
                workouts = {}
                for row in rows:
                    session_id, date, set_num, weight, reps, rpe, form_quality = row

                    if session_id not in workouts:
                        workouts[session_id] = {
                            'session_id': session_id,
                            'date': date,
                            'sets': []
                        }

                    workouts[session_id]['sets'].append({
                        'set_number': set_num,
                        'weight': weight,
                        'reps': reps,
                        'rpe': rpe,
                        'form_quality': form_quality
                    })

                # Sort sets within each workout
                workout_list = list(workouts.values())
                for workout in workout_list:
                    workout['sets'].sort(key=lambda x: x['set_number'])

                return workout_list

        except Exception as e:
            logger.error(f"Error getting recent workouts: {e}")
            return []

    def get_exercise_performance_stats(self, user_id: int, exercise_id: int, days: int = 30) -> Dict:
        """Get performance statistics for an exercise"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT
                        MAX(wset.weight) as max_weight,
                        AVG(wset.weight) as avg_weight,
                        MAX(wset.reps) as max_reps,
                        AVG(wset.reps) as avg_reps,
                        COUNT(DISTINCT ws.id) as workout_count,
                        COUNT(wset.id) as total_sets
                    FROM workout_sessions ws
                    JOIN workout_sets wset ON ws.id = wset.session_id
                    WHERE ws.user_id = %s AND wset.exercise_id = %s
                          AND ws.date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                          AND ws.status = 'completed'
                ''', (user_id, exercise_id, days))

                row = cursor.fetchone()
                if row and row[0]:  # Check if we have data
                    return {
                        'max_weight': float(row[0]),
                        'avg_weight': float(row[1]),
                        'max_reps': int(row[2]),
                        'avg_reps': float(row[3]),
                        'workout_count': int(row[4]),
                        'total_sets': int(row[5])
                    }
                return {}

        except Exception as e:
            logger.error(f"Error getting performance stats: {e}")
            return {}

    def get_volume_data(self, user_id: int, exercise_id: int, days: int = 30) -> List[Dict]:
        """Get volume data points for trend analysis"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT ws.date,
                           SUM(wset.weight * wset.reps) as total_volume,
                           AVG(wset.weight) as avg_intensity,
                           COUNT(wset.id) as total_sets
                    FROM workout_sessions ws
                    JOIN workout_sets wset ON ws.id = wset.session_id
                    WHERE ws.user_id = %s AND wset.exercise_id = %s
                          AND ws.date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                          AND ws.status = 'completed'
                    GROUP BY ws.date
                    ORDER BY ws.date
                ''', (user_id, exercise_id, days))

                rows = cursor.fetchall()
                return [{
                    'date': row[0],
                    'total_volume': float(row[1]) if row[1] else 0,
                    'avg_intensity': float(row[2]) if row[2] else 0,
                    'total_sets': int(row[3])
                } for row in rows]

        except Exception as e:
            logger.error(f"Error getting volume data: {e}")
            return []

    def check_user_has_workouts(self, user_id: int, min_workouts: int = 3) -> bool:
        """Check if user has minimum number of completed workouts"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM workout_sessions
                    WHERE user_id = %s AND status = 'completed'
                ''', (user_id,))

                count = cursor.fetchone()[0]
                return count >= min_workouts

        except Exception as e:
            logger.error(f"Error checking user workouts: {e}")
            return False
