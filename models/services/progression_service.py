"""
Progressive Overload Service for Gym Tracker
Handles progression detection, suggestions, and tracking
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import statistics

class ProgressionService:
    def __init__(self, db_path='database.db'):
        self.db_path = db_path

    def get_user_preferences(self, user_id: int) -> Dict:
        """Get user's gym preferences"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT progression_strategy, min_reps_target, max_reps_target,
                   weight_increment_upper, weight_increment_lower,
                   rest_timer_enabled, progression_notification_enabled
            FROM user_gym_preferences
            WHERE user_id = ?
        ''', (user_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'progression_strategy': row[0],
                'min_reps_target': row[1],
                'max_reps_target': row[2],
                'weight_increment_upper': row[3],
                'weight_increment_lower': row[4],
                'rest_timer_enabled': bool(row[5]),
                'progression_notification_enabled': bool(row[6])
            }
        else:
            # Return defaults if no preferences found
            return {
                'progression_strategy': 'reps_first',
                'min_reps_target': 10,
                'max_reps_target': 15,
                'weight_increment_upper': 2.5,
                'weight_increment_lower': 5.0,
                'rest_timer_enabled': True,
                'progression_notification_enabled': True
            }

    def update_user_preferences(self, user_id: int, preferences: Dict) -> bool:
        """Update user's gym preferences"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT OR REPLACE INTO user_gym_preferences
                (user_id, progression_strategy, min_reps_target, max_reps_target,
                 weight_increment_upper, weight_increment_lower,
                 rest_timer_enabled, progression_notification_enabled,
                 updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                user_id,
                preferences.get('progression_strategy', 'reps_first'),
                preferences.get('min_reps_target', 10),
                preferences.get('max_reps_target', 15),
                preferences.get('weight_increment_upper', 2.5),
                preferences.get('weight_increment_lower', 5.0),
                preferences.get('rest_timer_enabled', True),
                preferences.get('progression_notification_enabled', True)
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
        """Get last N performances for an exercise"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT ws.id, ws.date, wset.weight, wset.reps, wset.set_number,
                   wset.rpe, wset.form_quality
            FROM workout_sessions ws
            JOIN workout_sets wset ON ws.id = wset.session_id
            WHERE ws.user_id = ? AND wset.exercise_id = ?
                  AND ws.status = 'completed'
            ORDER BY ws.date DESC, wset.set_number
            LIMIT ?
        ''', (user_id, exercise_id, limit * 10))  # Get more to ensure we have enough workouts

        rows = cursor.fetchall()
        conn.close()

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

    def check_progression_readiness(self, user_id: int, exercise_id: int) -> Dict:
        """Check if user is ready to progress on an exercise"""
        prefs = self.get_user_preferences(user_id)
        history = self.get_exercise_performance_history(user_id, exercise_id, limit=3)

        if len(history) < 2:
            return {
                'ready': False,
                'reason': 'Not enough workout history',
                'suggestion': 'Complete at least 2 more workouts'
            }

        # Get exercise info to determine if upper or lower body
        exercise_info = self._get_exercise_info(exercise_id)
        is_upper_body = self._is_upper_body_exercise(exercise_info)

        if prefs['progression_strategy'] == 'reps_first':
            return self._check_reps_first_progression(history, prefs, is_upper_body)
        elif prefs['progression_strategy'] == 'weight_first':
            return self._check_weight_first_progression(history, prefs, is_upper_body)
        else:
            return self._check_hybrid_progression(history, prefs, is_upper_body)

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
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT name, muscle_group, equipment
            FROM exercises
            WHERE id = ?
        ''', (exercise_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'name': row[0],
                'muscle_group': row[1],
                'equipment': row[2]
            }
        return {}

    def record_progression(self, user_id: int, exercise_id: int,
                          old_weight: float, new_weight: float,
                          progression_type: str = 'weight_increase',
                          notes: str = '') -> bool:
        """Record a progression event"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO progression_history
                (user_id, exercise_id, progression_date, old_weight, new_weight,
                 progression_type, notes)
                VALUES (?, ?, DATE('now'), ?, ?, ?, ?)
            ''', (user_id, exercise_id, old_weight, new_weight,
                  progression_type, notes))

            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error recording progression: {e}")
            return False
        finally:
            conn.close()

    def get_progression_suggestions(self, user_id: int, workout_id: Optional[int] = None) -> List[Dict]:
        """Get progression suggestions for user's exercises"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get exercises from current workout or recent workouts
        if workout_id:
            cursor.execute('''
                SELECT DISTINCT exercise_id
                FROM workout_sets
                WHERE session_id = ?
            ''', (workout_id,))
        else:
            # Get exercises from last 5 workouts
            cursor.execute('''
                SELECT DISTINCT wset.exercise_id
                FROM workout_sessions ws
                JOIN workout_sets wset ON ws.id = wset.session_id
                WHERE ws.user_id = ? AND ws.status = 'completed'
                ORDER BY ws.date DESC
                LIMIT 50
            ''', (user_id,))

        exercise_ids = [row[0] for row in cursor.fetchall()]
        conn.close()

        # Check progression for each exercise
        suggestions = []
        for exercise_id in set(exercise_ids):  # Remove duplicates
            readiness = self.check_progression_readiness(user_id, exercise_id)
            exercise_info = self._get_exercise_info(exercise_id)

            suggestions.append({
                'exercise_id': exercise_id,
                'exercise_name': exercise_info.get('name', 'Unknown'),
                'muscle_group': exercise_info.get('muscle_group', ''),
                **readiness
            })

        # Sort by readiness (ready first) and exercise name
        suggestions.sort(key=lambda x: (not x.get('ready', False), x['exercise_name']))

        return suggestions

    def get_exercise_trend(self, user_id: int, exercise_id: int, days: int = 30) -> Dict:
        """Get exercise performance trend over time"""
        conn = sqlite3.connect(self.db_path)
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
