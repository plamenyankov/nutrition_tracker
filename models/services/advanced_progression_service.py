"""
Advanced Progressive Overload Service for Gym Tracker
Handles set-specific progression, pyramid patterns, and volume analysis
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import statistics
import os

class AdvancedProgressionService:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.getenv('DATABASE_PATH', 'database.db')
        self.db_path = db_path

    def _get_connection(self):
        """Get a database connection with WAL mode enabled"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def analyze_set_progression(self, user_id: int, exercise_id: int, set_number: int) -> Dict:
        """Analyze progression readiness for a specific set"""
        # Get last 3-5 performances for this specific set
        history = self.get_set_history(user_id, exercise_id, set_number, limit=5)

        if len(history) < 2:
            return {
                'ready': False,
                'confidence': 0.0,
                'suggestion': 'Need more workout history',
                'reps_to_go': None
            }

        # Get user preferences
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT min_reps_target, max_reps_target, weight_increment_upper, weight_increment_lower
            FROM user_gym_preferences
            WHERE user_id = ?
        ''', (user_id,))

        prefs = cursor.fetchone()
        conn.close()

        if not prefs:
            min_reps, max_reps, inc_upper, inc_lower = 10, 15, 2.5, 5.0
        else:
            min_reps, max_reps, inc_upper, inc_lower = prefs

        # Analyze recent performance
        recent_weights = [h['weight'] for h in history[:3]]
        recent_reps = [h['reps'] for h in history[:3]]

        # Check if consistently hitting max reps
        hitting_max_reps = all(r >= max_reps for r in recent_reps[:2])
        avg_reps = statistics.mean(recent_reps[:2])

        # Determine if upper or lower body exercise
        is_upper = self._is_upper_body_exercise(exercise_id)
        weight_increment = inc_upper if is_upper else inc_lower

        if hitting_max_reps:
            # Ready to progress in weight
            current_weight = recent_weights[0]
            return {
                'ready': True,
                'confidence': 0.9,
                'suggestion': 'increase_weight',
                'current_weight': current_weight,
                'suggested_weight': current_weight + weight_increment,
                'suggested_reps': min_reps,
                'reps_to_go': 0
            }
        elif avg_reps >= max_reps - 1:
            # Close to progression
            return {
                'ready': False,
                'confidence': 0.6,
                'suggestion': 'almost_ready',
                'current_weight': recent_weights[0],
                'reps_to_go': max(1, int(max_reps - avg_reps)),
                'target_reps': max_reps
            }
        else:
            # Focus on increasing reps
            return {
                'ready': False,
                'confidence': 0.3,
                'suggestion': 'increase_reps',
                'current_weight': recent_weights[0],
                'current_avg_reps': round(avg_reps, 1),
                'reps_to_go': int(max_reps - avg_reps),
                'target_reps': max_reps
            }

    def get_set_history(self, user_id: int, exercise_id: int, set_number: int, limit: int = 5) -> List[Dict]:
        """Get history for a specific set number"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT ws.date, wset.weight, wset.reps, wset.rpe, wset.form_quality
            FROM workout_sets wset
            JOIN workout_sessions ws ON wset.session_id = ws.id
            WHERE ws.user_id = ? AND wset.exercise_id = ? AND wset.set_number = ?
                  AND ws.status = 'completed'
            ORDER BY ws.date DESC
            LIMIT ?
        ''', (user_id, exercise_id, set_number, limit))

        rows = cursor.fetchall()
        conn.close()

        return [{
            'date': row[0],
            'weight': row[1],
            'reps': row[2],
            'rpe': row[3],
            'form_quality': row[4]
        } for row in rows]

    def detect_pyramid_pattern(self, user_id: int, exercise_id: int) -> Dict:
        """Detect the user's typical pyramid pattern for an exercise"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get recent workouts with multiple sets
        cursor.execute('''
            SELECT ws.id, ws.date
            FROM workout_sessions ws
            WHERE ws.user_id = ? AND ws.status = 'completed'
                  AND EXISTS (
                      SELECT 1 FROM workout_sets wset
                      WHERE wset.session_id = ws.id AND wset.exercise_id = ?
                  )
            ORDER BY ws.date DESC
            LIMIT 5
        ''', (user_id, exercise_id))

        workouts = cursor.fetchall()
        patterns = []

        for workout_id, _ in workouts:
            # Get all sets for this exercise in this workout
            cursor.execute('''
                SELECT set_number, weight, reps
                FROM workout_sets
                WHERE session_id = ? AND exercise_id = ?
                ORDER BY set_number
            ''', (workout_id, exercise_id))

            sets = cursor.fetchall()

            if len(sets) >= 2:
                weights = [s[1] for s in sets]
                weight_diffs = [weights[i+1] - weights[i] for i in range(len(weights)-1)]

                if all(diff > 0 for diff in weight_diffs):
                    patterns.append('ascending')
                elif all(diff < 0 for diff in weight_diffs):
                    patterns.append('descending')
                elif all(abs(diff) < 2.5 for diff in weight_diffs):
                    patterns.append('straight')
                else:
                    patterns.append('mixed')

        conn.close()

        if not patterns:
            return {
                'pattern': 'unknown',
                'confidence': 0.0,
                'typical_sets': 3
            }

        # Find most common pattern
        pattern_counts = {p: patterns.count(p) for p in set(patterns)}
        most_common = max(pattern_counts, key=pattern_counts.get)
        confidence = pattern_counts[most_common] / len(patterns)

        return {
            'pattern': most_common,
            'confidence': confidence,
            'typical_sets': len(sets) if sets else 3,
            'pattern_distribution': pattern_counts
        }

    def suggest_set_addition(self, user_id: int, exercise_id: int) -> Dict:
        """Suggest when to add a new set to an exercise"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get current typical set count
        cursor.execute('''
            SELECT MAX(set_number) as max_sets
            FROM workout_sets wset
            JOIN workout_sessions ws ON wset.session_id = ws.id
            WHERE ws.user_id = ? AND wset.exercise_id = ?
                  AND ws.date >= date('now', '-30 days')
                  AND ws.status = 'completed'
            GROUP BY ws.id
            ORDER BY ws.date DESC
            LIMIT 3
        ''', (user_id, exercise_id))

        recent_set_counts = [row[0] for row in cursor.fetchall()]

        if not recent_set_counts:
            conn.close()
            return {'suggest_add_set': False, 'reason': 'No recent workout data'}

        current_sets = max(recent_set_counts)

        # Check performance on current last set
        last_set_history = self.get_set_history(user_id, exercise_id, current_sets, limit=3)

        if len(last_set_history) < 3:
            conn.close()
            return {'suggest_add_set': False, 'reason': 'Not enough history on current sets'}

        # Get user's rep targets
        cursor.execute('''
            SELECT min_reps_target, max_reps_target
            FROM user_gym_preferences
            WHERE user_id = ?
        ''', (user_id,))

        prefs = cursor.fetchone()
        min_reps = prefs[0] if prefs else 10

        # Check if consistently performing well on last set
        last_set_reps = [h['reps'] for h in last_set_history[:3]]
        avg_last_set_reps = statistics.mean(last_set_reps)

        # Get pyramid pattern
        pattern_info = self.detect_pyramid_pattern(user_id, exercise_id)

        # Suggest new set if:
        # 1. Consistently hitting good reps on last set (>= min_reps)
        # 2. Has been doing current set count for at least 3 workouts
        # 3. Not already at 6+ sets (diminishing returns)

        if (avg_last_set_reps >= min_reps and
            all(c == current_sets for c in recent_set_counts[:3]) and
            current_sets < 6):

            # Calculate suggested weight for new set
            if pattern_info['pattern'] == 'ascending':
                # Increase weight from last set
                last_weight = last_set_history[0]['weight']
                suggested_weight = last_weight + (2.5 if self._is_upper_body_exercise(exercise_id) else 5.0)
            elif pattern_info['pattern'] == 'descending':
                # Decrease weight from last set
                last_weight = last_set_history[0]['weight']
                suggested_weight = max(20, last_weight - 5.0)  # Don't go below 20kg
            else:
                # Same weight as last set
                suggested_weight = last_set_history[0]['weight']

            conn.close()
            return {
                'suggest_add_set': True,
                'reason': f'Consistently performing well on set {current_sets}',
                'current_sets': current_sets,
                'new_set_number': current_sets + 1,
                'suggested_weight': suggested_weight,
                'suggested_reps': 6,  # Start conservative with new set
                'pattern': pattern_info['pattern']
            }

        conn.close()
        return {
            'suggest_add_set': False,
            'reason': f'Focus on current {current_sets} sets',
            'current_performance': f'Averaging {avg_last_set_reps:.1f} reps on last set'
        }

    def calculate_volume_metrics(self, workout_id: int, exercise_id: int) -> Dict:
        """Calculate and store volume metrics for a workout"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get all sets for this exercise in this workout
        cursor.execute('''
            SELECT weight, reps
            FROM workout_sets
            WHERE session_id = ? AND exercise_id = ?
        ''', (workout_id, exercise_id))

        sets = cursor.fetchall()

        if not sets:
            conn.close()
            return {'error': 'No sets found'}

        # Calculate metrics
        total_volume = sum(weight * reps for weight, reps in sets)
        total_reps = sum(reps for _, reps in sets)
        total_sets = len(sets)
        avg_intensity = statistics.mean(weight for weight, _ in sets)

        # Store in database
        cursor.execute('''
            INSERT OR REPLACE INTO workout_volume_tracking
            (workout_id, exercise_id, total_volume, total_reps, total_sets, avg_intensity)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (workout_id, exercise_id, total_volume, total_reps, total_sets, avg_intensity))

        conn.commit()
        conn.close()

        return {
            'total_volume': total_volume,
            'total_reps': total_reps,
            'total_sets': total_sets,
            'avg_intensity': round(avg_intensity, 1)
        }

    def get_volume_trend(self, user_id: int, exercise_id: int, days: int = 30) -> Dict:
        """Get volume trend for an exercise over specified days"""
        conn = self._get_connection()
        cursor = conn.cursor()

        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        cursor.execute('''
            SELECT ws.date, vt.total_volume, vt.avg_intensity, vt.total_sets
            FROM workout_sessions ws
            JOIN workout_volume_tracking vt ON ws.id = vt.workout_id
            WHERE ws.user_id = ? AND vt.exercise_id = ?
                  AND ws.date >= ? AND ws.status = 'completed'
            ORDER BY ws.date
        ''', (user_id, exercise_id, start_date))

        data = cursor.fetchall()
        conn.close()

        if len(data) < 2:
            return {
                'trend': 'insufficient_data',
                'volume_change_percent': 0,
                'intensity_change_percent': 0
            }

        # Calculate trends
        first_volume = data[0][1]
        last_volume = data[-1][1]
        first_intensity = data[0][2]
        last_intensity = data[-1][2]

        volume_change = ((last_volume - first_volume) / first_volume) * 100 if first_volume > 0 else 0
        intensity_change = ((last_intensity - first_intensity) / first_intensity) * 100 if first_intensity > 0 else 0

        # Determine trend
        if volume_change > 10:
            trend = 'increasing'
        elif volume_change < -10:
            trend = 'decreasing'
        else:
            trend = 'stable'

        return {
            'trend': trend,
            'volume_change_percent': round(volume_change, 1),
            'intensity_change_percent': round(intensity_change, 1),
            'data_points': len(data),
            'first_date': data[0][0],
            'last_date': data[-1][0]
        }

    def _is_upper_body_exercise(self, exercise_id: int) -> bool:
        """Determine if exercise is upper body based on muscle groups"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT name, muscle_group
            FROM exercises
            WHERE id = ?
        ''', (exercise_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return True  # Default to upper body

        name, muscle_group = row[0].lower() if row[0] else '', row[1].lower() if row[1] else ''

        lower_body_keywords = ['leg', 'glute', 'quad', 'hamstring', 'calf', 'squat', 'deadlift', 'lunge']

        for keyword in lower_body_keywords:
            if keyword in name or keyword in muscle_group:
                return False

        return True

    def record_set_progression(self, user_id: int, exercise_id: int, set_number: int,
                               old_weight: float, new_weight: float, old_reps: int,
                               new_reps: int, progression_type: str, notes: str = '') -> bool:
        """Record a set-specific progression event"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO set_progression_history
                (user_id, exercise_id, set_number, progression_date,
                 old_weight, new_weight, old_reps, new_reps,
                 progression_type, notes)
                VALUES (?, ?, ?, DATE('now'), ?, ?, ?, ?, ?, ?)
            ''', (user_id, exercise_id, set_number, old_weight, new_weight,
                  old_reps, new_reps, progression_type, notes))

            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error recording set progression: {e}")
            return False
        finally:
            conn.close()
