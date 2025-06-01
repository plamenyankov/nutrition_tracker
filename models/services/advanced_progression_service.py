"""
Advanced Progressive Overload Service
Handles set-specific progression, pyramid pattern detection, and volume tracking
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

    def get_set_history(self, user_id: int, exercise_id: int, set_number: int,
                       limit: int = 5) -> List[Dict]:
        """Get history for a specific set number of an exercise"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT ws.date, wset.weight, wset.reps, wset.rpe, wset.form_quality,
                   wset.id as set_id, ws.id as workout_id
            FROM workout_sessions ws
            JOIN workout_sets wset ON ws.id = wset.session_id
            WHERE ws.user_id = ? AND wset.exercise_id = ?
                  AND wset.set_number = ? AND ws.status = 'completed'
            ORDER BY ws.date DESC
            LIMIT ?
        ''', (user_id, exercise_id, set_number, limit))

        rows = cursor.fetchall()
        conn.close()

        history = []
        for row in rows:
            history.append({
                'date': row[0],
                'weight': row[1],
                'reps': row[2],
                'rpe': row[3],
                'form_quality': row[4],
                'set_id': row[5],
                'workout_id': row[6]
            })

        return history

    def analyze_set_progression(self, user_id: int, exercise_id: int,
                               set_number: int) -> Dict:
        """Analyze progression readiness for a specific set"""
        history = self.get_set_history(user_id, exercise_id, set_number, limit=3)

        if len(history) < 2:
            return {
                'ready': False,
                'confidence': 0,
                'reason': 'Not enough history',
                'suggestion': 'Complete more workouts'
            }

        # Get user preferences
        prefs = self._get_user_preferences(user_id)
        max_reps_target = prefs['max_reps_target']

        # Check last 2-3 performances
        recent_reps = [h['reps'] for h in history[:3]]
        recent_weights = [h['weight'] for h in history[:3]]

        # Check if consistently hitting max reps
        if all(r >= max_reps_target for r in recent_reps[:2]):
            # Ready to increase weight
            weight_increment = self._get_weight_increment(user_id, exercise_id)
            return {
                'ready': True,
                'confidence': 0.9,
                'suggestion_type': 'increase_weight',
                'current_weight': recent_weights[0],
                'suggested_weight': recent_weights[0] + weight_increment,
                'suggested_reps': prefs['min_reps_target'],
                'reason': f'Consistently hit {max_reps_target} reps'
            }

        # Check if close to progression
        avg_reps = statistics.mean(recent_reps[:2])
        if avg_reps >= max_reps_target - 2:
            return {
                'ready': False,
                'confidence': 0.6,
                'suggestion_type': 'increase_reps',
                'current_reps': int(avg_reps),
                'target_reps': max_reps_target,
                'reps_to_go': max_reps_target - int(avg_reps),
                'reason': f'Almost there! {max_reps_target - int(avg_reps)} more reps to go'
            }

        return {
            'ready': False,
            'confidence': 0.3,
            'suggestion_type': 'maintain',
            'current_reps': int(avg_reps),
            'target_reps': max_reps_target,
            'reason': 'Keep working on current weight'
        }

    def detect_pyramid_pattern(self, user_id: int, exercise_id: int) -> Dict:
        """Detect the user's typical pyramid pattern for an exercise"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get last 5 workouts with this exercise
        cursor.execute('''
            SELECT ws.id, ws.date
            FROM workout_sessions ws
            JOIN workout_sets wset ON ws.id = wset.session_id
            WHERE ws.user_id = ? AND wset.exercise_id = ?
                  AND ws.status = 'completed'
            GROUP BY ws.id
            ORDER BY ws.date DESC
            LIMIT 5
        ''', (user_id, exercise_id))

        workouts = cursor.fetchall()

        patterns = []
        for workout_id, date in workouts:
            # Get all sets for this workout/exercise
            cursor.execute('''
                SELECT set_number, weight
                FROM workout_sets
                WHERE session_id = ? AND exercise_id = ?
                ORDER BY set_number
            ''', (workout_id, exercise_id))

            sets = cursor.fetchall()
            if len(sets) >= 2:
                weights = [s[1] for s in sets]
                pattern = self._classify_pattern(weights)
                patterns.append(pattern)

        conn.close()

        if not patterns:
            return {'pattern': 'unknown', 'confidence': 0}

        # Find most common pattern
        pattern_counts = {}
        for p in patterns:
            pattern_counts[p] = pattern_counts.get(p, 0) + 1

        most_common = max(pattern_counts, key=pattern_counts.get)
        confidence = pattern_counts[most_common] / len(patterns)

        return {
            'pattern': most_common,
            'confidence': confidence,
            'sample_size': len(patterns)
        }

    def _classify_pattern(self, weights: List[float]) -> str:
        """Classify a weight sequence into a pyramid pattern"""
        if len(weights) < 2:
            return 'single_set'

        # Calculate differences
        diffs = [weights[i+1] - weights[i] for i in range(len(weights)-1)]

        # Check patterns
        if all(d > 0 for d in diffs):
            return 'ascending'
        elif all(d < 0 for d in diffs):
            return 'descending'
        elif all(abs(d) < 2.5 for d in diffs):  # Within 2.5kg is considered "same"
            return 'straight'
        elif len(weights) >= 3:
            # Check for pyramid patterns
            if weights[0] < weights[len(weights)//2] > weights[-1]:
                return 'pyramid'
            elif weights[0] > weights[len(weights)//2] < weights[-1]:
                return 'reverse_pyramid'

        return 'mixed'

    def calculate_volume_metrics(self, workout_id: int, exercise_id: int) -> Dict:
        """Calculate and store volume metrics for an exercise in a workout"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all sets
        cursor.execute('''
            SELECT weight, reps
            FROM workout_sets
            WHERE session_id = ? AND exercise_id = ?
        ''', (workout_id, exercise_id))

        sets = cursor.fetchall()

        if not sets:
            conn.close()
            return {}

        # Calculate metrics
        total_volume = sum(weight * reps for weight, reps in sets)
        total_reps = sum(reps for _, reps in sets)
        total_sets = len(sets)
        weights = [weight for weight, _ in sets]
        avg_intensity = statistics.mean(weights)
        max_weight = max(weights)
        tonnage = total_volume / 1000  # Convert to metric tons

        # Store in database
        cursor.execute('''
            INSERT OR REPLACE INTO workout_volume_tracking
            (workout_id, exercise_id, total_volume, total_reps,
             total_sets, avg_intensity, max_weight, tonnage)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (workout_id, exercise_id, total_volume, total_reps,
              total_sets, avg_intensity, max_weight, tonnage))

        conn.commit()
        conn.close()

        return {
            'total_volume': total_volume,
            'total_reps': total_reps,
            'total_sets': total_sets,
            'avg_intensity': round(avg_intensity, 1),
            'max_weight': max_weight,
            'tonnage': round(tonnage, 3)
        }

    def get_volume_trend(self, user_id: int, exercise_id: int,
                        days: int = 30) -> Dict:
        """Analyze volume trend over time"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        cursor.execute('''
            SELECT ws.date, vt.total_volume, vt.total_reps, vt.avg_intensity,
                   vt.total_sets, vt.max_weight
            FROM workout_volume_tracking vt
            JOIN workout_sessions ws ON vt.workout_id = ws.id
            WHERE ws.user_id = ? AND vt.exercise_id = ?
                  AND ws.date >= ? AND ws.status = 'completed'
            ORDER BY ws.date
        ''', (user_id, exercise_id, start_date))

        data = cursor.fetchall()
        conn.close()

        if len(data) < 2:
            return {'trend': 'insufficient_data', 'data_points': []}

        volumes = [row[1] for row in data]
        intensities = [row[3] for row in data]

        # Calculate trends (simple linear regression would be better)
        volume_change = ((volumes[-1] - volumes[0]) / volumes[0]) * 100 if volumes[0] > 0 else 0
        intensity_change = ((intensities[-1] - intensities[0]) / intensities[0]) * 100 if intensities[0] > 0 else 0

        return {
            'volume_trend': 'increasing' if volume_change > 5 else 'decreasing' if volume_change < -5 else 'stable',
            'intensity_trend': 'increasing' if intensity_change > 5 else 'decreasing' if intensity_change < -5 else 'stable',
            'volume_change_percent': round(volume_change, 1),
            'intensity_change_percent': round(intensity_change, 1),
            'data_points': [{
                'date': row[0],
                'volume': row[1],
                'reps': row[2],
                'avg_weight': row[3],
                'sets': row[4],
                'max_weight': row[5]
            } for row in data]
        }

    def suggest_set_targets(self, user_id: int, exercise_id: int,
                           current_sets: List[Dict]) -> List[Dict]:
        """Suggest targets for each set based on pyramid pattern and progression"""
        pattern_info = self.detect_pyramid_pattern(user_id, exercise_id)
        pattern = pattern_info['pattern']

        suggestions = []

        for i, current_set in enumerate(current_sets):
            set_number = i + 1
            progression = self.analyze_set_progression(user_id, exercise_id, set_number)

            suggestion = {
                'set_number': set_number,
                'current_weight': current_set.get('weight', 0),
                'current_reps': current_set.get('reps', 0),
                'progression_analysis': progression
            }

            # Add pattern-specific suggestions
            if pattern == 'ascending' and i > 0:
                # Each set should be heavier than the last
                prev_weight = suggestions[i-1]['suggested_weight']
                weight_jump = 5.0 if self._is_lower_body_exercise(exercise_id) else 2.5
                suggestion['suggested_weight'] = prev_weight + weight_jump
            elif pattern == 'descending' and i > 0:
                # Each set should be lighter
                prev_weight = suggestions[i-1]['suggested_weight']
                weight_drop = 5.0 if self._is_lower_body_exercise(exercise_id) else 2.5
                suggestion['suggested_weight'] = max(0, prev_weight - weight_drop)
            else:
                # Use progression analysis suggestion
                if progression.get('ready') and 'suggested_weight' in progression:
                    suggestion['suggested_weight'] = progression['suggested_weight']
                else:
                    suggestion['suggested_weight'] = current_set.get('weight', 0)

            suggestions.append(suggestion)

        return suggestions

    def record_set_progression(self, user_id: int, exercise_id: int,
                              set_number: int, old_weight: float, new_weight: float,
                              old_reps: int, new_reps: int,
                              progression_type: str = 'weight') -> bool:
        """Record progression for a specific set"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO set_progression_history
                (user_id, exercise_id, set_number, progression_date,
                 old_weight, new_weight, old_reps, new_reps, progression_type)
                VALUES (?, ?, ?, DATE('now'), ?, ?, ?, ?, ?)
            ''', (user_id, exercise_id, set_number, old_weight, new_weight,
                  old_reps, new_reps, progression_type))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error recording set progression: {e}")
            conn.close()
            return False

    def _get_user_preferences(self, user_id: int) -> Dict:
        """Get user preferences with defaults"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT min_reps_target, max_reps_target,
                   weight_increment_upper, weight_increment_lower,
                   progression_priority_1, progression_priority_2,
                   progression_priority_3, pyramid_preference
            FROM user_gym_preferences
            WHERE user_id = ?
        ''', (user_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'min_reps_target': row[0],
                'max_reps_target': row[1],
                'weight_increment_upper': row[2],
                'weight_increment_lower': row[3],
                'priority_1': row[4],
                'priority_2': row[5],
                'priority_3': row[6],
                'pyramid_preference': row[7]
            }

        # Return defaults
        return {
            'min_reps_target': 10,
            'max_reps_target': 15,
            'weight_increment_upper': 2.5,
            'weight_increment_lower': 5.0,
            'priority_1': 'reps',
            'priority_2': 'weight',
            'priority_3': 'volume',
            'pyramid_preference': 'auto_detect'
        }

    def _get_weight_increment(self, user_id: int, exercise_id: int) -> float:
        """Get appropriate weight increment for exercise"""
        prefs = self._get_user_preferences(user_id)

        if self._is_lower_body_exercise(exercise_id):
            return prefs['weight_increment_lower']
        else:
            return prefs['weight_increment_upper']

    def _is_lower_body_exercise(self, exercise_id: int) -> bool:
        """Check if exercise is lower body"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT name, muscle_group
            FROM exercises
            WHERE id = ?
        ''', (exercise_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return False

        name, muscle_group = row[0].lower(), (row[1] or '').lower()
        lower_body_keywords = ['leg', 'glute', 'quad', 'hamstring', 'calf',
                              'squat', 'deadlift', 'lunge']

        return any(keyword in name or keyword in muscle_group
                  for keyword in lower_body_keywords)

    def suggest_set_addition(self, user_id: int, exercise_id: int) -> Dict:
        """Analyze if user should add another set to their exercise"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get current typical set count
        cursor.execute('''
            SELECT typical_sets FROM exercise_progression_patterns
            WHERE user_id = ? AND exercise_id = ?
        ''', (user_id, exercise_id))

        row = cursor.fetchone()
        current_sets = row[0] if row else 3

        # Get last 4 workouts performance
        cursor.execute('''
            SELECT ws.id, ws.date, COUNT(DISTINCT wset.set_number) as set_count,
                   AVG(CASE WHEN wset.reps >= ? THEN 1 ELSE 0 END) as success_rate
            FROM workout_sessions ws
            JOIN workout_sets wset ON ws.id = wset.session_id
            JOIN user_gym_preferences ugp ON ugp.user_id = ws.user_id
            WHERE ws.user_id = ? AND wset.exercise_id = ?
                  AND ws.status = 'completed'
            GROUP BY ws.id
            ORDER BY ws.date DESC
            LIMIT 4
        ''', (self._get_user_preferences(user_id)['max_reps_target'],
              user_id, exercise_id))

        workouts = cursor.fetchall()
        conn.close()

        if len(workouts) < 3:
            return {
                'suggest_add_set': False,
                'reason': 'Need more workout history',
                'current_sets': current_sets
            }

        # Check if consistently hitting targets
        success_rates = [w[3] for w in workouts]
        avg_success = statistics.mean(success_rates)

        # Check if already at volume cap
        if current_sets >= 6:
            return {
                'suggest_add_set': False,
                'reason': 'Already at maximum recommended sets',
                'current_sets': current_sets,
                'suggestion': 'Focus on weight progression instead'
            }

        # Suggest adding set if high success rate
        if avg_success >= 0.85:  # 85% of sets hitting target reps
            weight_suggestion = self._calculate_new_set_weight(user_id, exercise_id, current_sets)

            return {
                'suggest_add_set': True,
                'reason': f'Consistently hitting targets on all {current_sets} sets',
                'current_sets': current_sets,
                'new_set_number': current_sets + 1,
                'suggested_weight': weight_suggestion,
                'suggested_reps': '6-8',
                'confidence': avg_success
            }

        return {
            'suggest_add_set': False,
            'reason': 'Master current sets first',
            'current_sets': current_sets,
            'success_rate': round(avg_success * 100),
            'target_success_rate': 85
        }

    def _calculate_new_set_weight(self, user_id: int, exercise_id: int,
                                 current_sets: int) -> float:
        """Calculate appropriate weight for a new set"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get the weight from the last set of recent workouts
        cursor.execute('''
            SELECT wset.weight
            FROM workout_sessions ws
            JOIN workout_sets wset ON ws.id = wset.session_id
            WHERE ws.user_id = ? AND wset.exercise_id = ?
                  AND wset.set_number = ? AND ws.status = 'completed'
            ORDER BY ws.date DESC
            LIMIT 3
        ''', (user_id, exercise_id, current_sets))

        last_set_weights = [row[0] for row in cursor.fetchall()]
        conn.close()

        if last_set_weights:
            avg_last_set = statistics.mean(last_set_weights)
            # New set should be 5-10% lighter
            return round(avg_last_set * 0.92, 1)  # 8% lighter

        return 0

    def update_pattern_ratios(self, user_id: int, exercise_id: int,
                             set_ratios: List[Dict]) -> bool:
        """Update the weight ratios for each set in a pattern"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Get or create pattern
            cursor.execute('''
                SELECT id FROM exercise_progression_patterns
                WHERE user_id = ? AND exercise_id = ?
            ''', (user_id, exercise_id))

            row = cursor.fetchone()
            if row:
                pattern_id = row[0]
            else:
                # Create new pattern
                cursor.execute('''
                    INSERT INTO exercise_progression_patterns
                    (user_id, exercise_id, typical_sets)
                    VALUES (?, ?, ?)
                ''', (user_id, exercise_id, len(set_ratios)))
                pattern_id = cursor.lastrowid

            # Update ratios
            for ratio_data in set_ratios:
                cursor.execute('''
                    INSERT OR REPLACE INTO set_pattern_ratios
                    (pattern_id, set_number, weight_ratio, typical_reps)
                    VALUES (?, ?, ?, ?)
                ''', (pattern_id, ratio_data['set_number'],
                      ratio_data['weight_ratio'], ratio_data['typical_reps']))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            print(f"Error updating pattern ratios: {e}")
            conn.rollback()
            conn.close()
            return False
