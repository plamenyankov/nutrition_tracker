"""
Advanced Progressive Overload Service for Gym Tracker
Handles set-specific progression, pyramid patterns, and volume analysis
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import statistics
import os
import logging
from dataclasses import dataclass
from enum import Enum

class PatternType(Enum):
    """Enhanced pattern types with more granular classification"""
    ASCENDING = "ascending"
    DESCENDING = "descending"
    STRAIGHT = "straight"
    PYRAMID = "pyramid"
    REVERSE_PYRAMID = "reverse_pyramid"
    WAVE = "wave"
    CLUSTER = "cluster"
    MIXED = "mixed"
    UNKNOWN = "unknown"

@dataclass
class PatternAnalysis:
    """Enhanced pattern analysis with confidence metrics"""
    pattern: PatternType
    confidence: float
    sample_size: int
    consistency_score: float
    trend_direction: str  # 'increasing', 'decreasing', 'stable'
    recommendation: str
    analysis_details: Dict[str, Any]

@dataclass
class ReadinessFactors:
    """Multi-factor readiness analysis"""
    rep_achievement_score: float  # 0-1
    consistency_score: float      # 0-1
    time_factor_score: float      # 0-1
    volume_trend_score: float     # 0-1
    form_quality_score: float     # 0-1
    overall_readiness: float      # 0-1
    recommendation: str

@dataclass
class SmartSuggestion:
    """Smart progression suggestions"""
    suggestion_type: str  # 'weight_increase', 'rep_increase', 'deload', 'plateau_break'
    current_value: float
    suggested_value: float
    confidence: float
    reasoning: str
    alternative_options: List[Dict[str, Any]]

class AdvancedProgressionService:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.getenv('DATABASE_PATH', 'database.db')
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)

        # Enhanced pattern detection parameters
        self.pattern_config = {
            'min_workouts_for_analysis': 3,
            'analysis_window': 8,  # Increased from 5
            'confidence_threshold': 0.7,
            'consistency_threshold': 0.8,
            'weight_change_threshold': 2.5,  # kg
            'rep_change_threshold': 2,
            'form_quality_weight': 0.15,
            'microloading_threshold': 1.25  # kg for advanced users
        }

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

    def detect_advanced_pattern(self, user_id: int, exercise_id: int) -> PatternAnalysis:
        """
        Enhanced pattern detection with multiple pattern types and confidence scoring
        """
        try:
            workout_history = self._get_workout_history(user_id, exercise_id,
                                                      self.pattern_config['analysis_window'])

            if len(workout_history) < self.pattern_config['min_workouts_for_analysis']:
                return PatternAnalysis(
                    pattern=PatternType.UNKNOWN,
                    confidence=0.0,
                    sample_size=len(workout_history),
                    consistency_score=0.0,
                    trend_direction='unknown',
                    recommendation='Need more workout data for pattern analysis',
                    analysis_details={}
                )

            # Analyze different pattern types
            pattern_scores = {}

            # Check for ascending pattern (pyramid up)
            pattern_scores[PatternType.ASCENDING] = self._analyze_ascending_pattern(workout_history)

            # Check for descending pattern (pyramid down)
            pattern_scores[PatternType.DESCENDING] = self._analyze_descending_pattern(workout_history)

            # Check for straight sets
            pattern_scores[PatternType.STRAIGHT] = self._analyze_straight_pattern(workout_history)

            # Check for pyramid pattern (up then down)
            pattern_scores[PatternType.PYRAMID] = self._analyze_pyramid_pattern(workout_history)

            # Check for reverse pyramid (down then up)
            pattern_scores[PatternType.REVERSE_PYRAMID] = self._analyze_reverse_pyramid_pattern(workout_history)

            # Check for wave pattern (alternating)
            pattern_scores[PatternType.WAVE] = self._analyze_wave_pattern(workout_history)

            # Check for cluster sets
            pattern_scores[PatternType.CLUSTER] = self._analyze_cluster_pattern(workout_history)

            # Determine dominant pattern
            best_pattern = max(pattern_scores.items(), key=lambda x: x[1]['confidence'])
            pattern_type, pattern_data = best_pattern

            # Calculate consistency across workouts
            consistency_score = self._calculate_pattern_consistency(workout_history, pattern_type)

            # Determine trend direction
            trend_direction = self._analyze_trend_direction(workout_history)

            # Generate recommendation
            recommendation = self._generate_pattern_recommendation(pattern_type, pattern_data,
                                                                 consistency_score, trend_direction)

            return PatternAnalysis(
                pattern=pattern_type,
                confidence=pattern_data['confidence'],
                sample_size=len(workout_history),
                consistency_score=consistency_score,
                trend_direction=trend_direction,
                recommendation=recommendation,
                analysis_details=pattern_data
            )

        except Exception as e:
            self.logger.error(f"Error in advanced pattern detection: {e}")
            return PatternAnalysis(
                pattern=PatternType.UNKNOWN,
                confidence=0.0,
                sample_size=0,
                consistency_score=0.0,
                trend_direction='unknown',
                recommendation='Error analyzing pattern',
                analysis_details={'error': str(e)}
            )

    def calculate_multi_factor_readiness(self, user_id: int, exercise_id: int) -> ReadinessFactors:
        """
        Multi-factor progression readiness analysis
        """
        try:
            # Get recent workout data
            recent_workouts = self._get_workout_history(user_id, exercise_id, 5)

            if not recent_workouts:
                return ReadinessFactors(0, 0, 0, 0, 0, 0, "No workout data available")

            # Factor 1: Rep Achievement Score (40% weight)
            rep_score = self._calculate_rep_achievement_score(recent_workouts)

            # Factor 2: Consistency Score (30% weight)
            consistency_score = self._calculate_workout_consistency(recent_workouts)

            # Factor 3: Time Factor Score (20% weight)
            time_score = self._calculate_time_factor_score(user_id, exercise_id)

            # Factor 4: Volume Trend Score (10% weight)
            volume_score = self._calculate_volume_trend_score(recent_workouts)

            # Factor 5: Form Quality Score (15% weight if available)
            form_score = self._calculate_form_quality_score(recent_workouts)

            # Calculate weighted overall readiness
            if form_score > 0:  # Form data available
                overall_readiness = (
                    rep_score * 0.35 +
                    consistency_score * 0.25 +
                    time_score * 0.15 +
                    volume_score * 0.10 +
                    form_score * 0.15
                )
            else:  # No form data
                overall_readiness = (
                    rep_score * 0.4 +
                    consistency_score * 0.3 +
                    time_score * 0.2 +
                    volume_score * 0.1
                )

            # Generate recommendation
            recommendation = self._generate_readiness_recommendation(overall_readiness, {
                'rep_score': rep_score,
                'consistency': consistency_score,
                'time_factor': time_score,
                'volume_trend': volume_score,
                'form_quality': form_score
            })

            return ReadinessFactors(
                rep_achievement_score=rep_score,
                consistency_score=consistency_score,
                time_factor_score=time_score,
                volume_trend_score=volume_score,
                form_quality_score=form_score,
                overall_readiness=overall_readiness,
                recommendation=recommendation
            )

        except Exception as e:
            self.logger.error(f"Error calculating readiness factors: {e}")
            return ReadinessFactors(0, 0, 0, 0, 0, 0, f"Error: {str(e)}")

    def generate_smart_suggestions(self, user_id: int, exercise_id: int) -> List[SmartSuggestion]:
        """
        Generate intelligent progression suggestions based on multiple factors
        """
        try:
            suggestions = []

            # Get current performance data
            current_performance = self._get_current_performance(user_id, exercise_id)
            if not current_performance:
                return suggestions

            # Get readiness analysis
            readiness = self.calculate_multi_factor_readiness(user_id, exercise_id)

            # Get pattern analysis
            pattern_analysis = self.detect_advanced_pattern(user_id, exercise_id)

            # Get progression history
            progression_history = self._get_progression_history(user_id, exercise_id)

            # Generate different types of suggestions

            # 1. Weight increase suggestions
            if readiness.overall_readiness >= 0.8:
                weight_suggestion = self._generate_weight_increase_suggestion(
                    current_performance, readiness, pattern_analysis, progression_history
                )
                if weight_suggestion:
                    suggestions.append(weight_suggestion)

            # 2. Rep increase suggestions
            if 0.6 <= readiness.overall_readiness < 0.8:
                rep_suggestion = self._generate_rep_increase_suggestion(
                    current_performance, readiness, pattern_analysis
                )
                if rep_suggestion:
                    suggestions.append(rep_suggestion)

            # 3. Deload suggestions
            if self._should_suggest_deload(progression_history, readiness):
                deload_suggestion = self._generate_deload_suggestion(
                    current_performance, progression_history
                )
                if deload_suggestion:
                    suggestions.append(deload_suggestion)

            # 4. Plateau breaking suggestions
            if self._detect_plateau(progression_history):
                plateau_suggestion = self._generate_plateau_break_suggestion(
                    current_performance, pattern_analysis, progression_history
                )
                if plateau_suggestion:
                    suggestions.append(plateau_suggestion)

            return suggestions

        except Exception as e:
            self.logger.error(f"Error generating smart suggestions: {e}")
            return []

    # Enhanced pattern analysis methods

    def _analyze_ascending_pattern(self, workout_history: List[Dict]) -> Dict[str, Any]:
        """Analyze ascending (pyramid up) pattern"""
        ascending_scores = []

        for workout in workout_history:
            sets = workout.get('sets', [])
            if len(sets) < 2:
                continue

            weight_increases = 0
            total_transitions = len(sets) - 1

            for i in range(len(sets) - 1):
                if sets[i+1]['weight'] > sets[i]['weight']:
                    weight_increases += 1

            if total_transitions > 0:
                ascending_scores.append(weight_increases / total_transitions)

        if not ascending_scores:
            return {'confidence': 0.0, 'details': 'No valid data'}

        confidence = statistics.mean(ascending_scores)
        return {
            'confidence': confidence,
            'details': f'Average ascending ratio: {confidence:.2f}',
            'sample_workouts': len(ascending_scores)
        }

    def _analyze_descending_pattern(self, workout_history: List[Dict]) -> Dict[str, Any]:
        """Analyze descending (pyramid down) pattern"""
        descending_scores = []

        for workout in workout_history:
            sets = workout.get('sets', [])
            if len(sets) < 2:
                continue

            weight_decreases = 0
            total_transitions = len(sets) - 1

            for i in range(len(sets) - 1):
                if sets[i+1]['weight'] < sets[i]['weight']:
                    weight_decreases += 1

            if total_transitions > 0:
                descending_scores.append(weight_decreases / total_transitions)

        if not descending_scores:
            return {'confidence': 0.0, 'details': 'No valid data'}

        confidence = statistics.mean(descending_scores)
        return {
            'confidence': confidence,
            'details': f'Average descending ratio: {confidence:.2f}',
            'sample_workouts': len(descending_scores)
        }

    def _analyze_straight_pattern(self, workout_history: List[Dict]) -> Dict[str, Any]:
        """Analyze straight sets pattern"""
        straight_scores = []

        for workout in workout_history:
            sets = workout.get('sets', [])
            if len(sets) < 2:
                continue

            same_weights = 0
            total_transitions = len(sets) - 1

            for i in range(len(sets) - 1):
                weight_diff = abs(sets[i+1]['weight'] - sets[i]['weight'])
                if weight_diff <= self.pattern_config['weight_change_threshold']:
                    same_weights += 1

            if total_transitions > 0:
                straight_scores.append(same_weights / total_transitions)

        if not straight_scores:
            return {'confidence': 0.0, 'details': 'No valid data'}

        confidence = statistics.mean(straight_scores)
        return {
            'confidence': confidence,
            'details': f'Average straight ratio: {confidence:.2f}',
            'sample_workouts': len(straight_scores)
        }

    def _analyze_pyramid_pattern(self, workout_history: List[Dict]) -> Dict[str, Any]:
        """Analyze pyramid (up then down) pattern"""
        pyramid_scores = []

        for workout in workout_history:
            sets = workout.get('sets', [])
            if len(sets) < 3:
                continue

            # Find peak weight
            weights = [s['weight'] for s in sets]
            max_weight = max(weights)
            max_index = weights.index(max_weight)

            # Check if weights increase to peak then decrease
            is_pyramid = True

            # Check ascending to peak
            for i in range(max_index):
                if weights[i+1] <= weights[i]:
                    is_pyramid = False
                    break

            # Check descending from peak
            if is_pyramid:
                for i in range(max_index, len(weights) - 1):
                    if weights[i+1] >= weights[i]:
                        is_pyramid = False
                        break

            pyramid_scores.append(1.0 if is_pyramid else 0.0)

        if not pyramid_scores:
            return {'confidence': 0.0, 'details': 'No valid data'}

        confidence = statistics.mean(pyramid_scores)
        return {
            'confidence': confidence,
            'details': f'Pyramid pattern frequency: {confidence:.2f}',
            'sample_workouts': len(pyramid_scores)
        }

    def _analyze_reverse_pyramid_pattern(self, workout_history: List[Dict]) -> Dict[str, Any]:
        """Analyze reverse pyramid (down then up) pattern"""
        reverse_pyramid_scores = []

        for workout in workout_history:
            sets = workout.get('sets', [])
            if len(sets) < 3:
                continue

            # Find minimum weight
            weights = [s['weight'] for s in sets]
            min_weight = min(weights)
            min_index = weights.index(min_weight)

            # Check if weights decrease to minimum then increase
            is_reverse_pyramid = True

            # Check descending to minimum
            for i in range(min_index):
                if weights[i+1] >= weights[i]:
                    is_reverse_pyramid = False
                    break

            # Check ascending from minimum
            if is_reverse_pyramid:
                for i in range(min_index, len(weights) - 1):
                    if weights[i+1] <= weights[i]:
                        is_reverse_pyramid = False
                        break

            reverse_pyramid_scores.append(1.0 if is_reverse_pyramid else 0.0)

        if not reverse_pyramid_scores:
            return {'confidence': 0.0, 'details': 'No valid data'}

        confidence = statistics.mean(reverse_pyramid_scores)
        return {
            'confidence': confidence,
            'details': f'Reverse pyramid pattern frequency: {confidence:.2f}',
            'sample_workouts': len(reverse_pyramid_scores)
        }

    def _analyze_wave_pattern(self, workout_history: List[Dict]) -> Dict[str, Any]:
        """Analyze wave (alternating) pattern"""
        wave_scores = []

        for workout in workout_history:
            sets = workout.get('sets', [])
            if len(sets) < 4:
                continue

            weights = [s['weight'] for s in sets]
            alternations = 0
            total_possible = len(weights) - 2

            for i in range(1, len(weights) - 1):
                # Check if current weight is different from both neighbors
                if ((weights[i] > weights[i-1] and weights[i] > weights[i+1]) or
                    (weights[i] < weights[i-1] and weights[i] < weights[i+1])):
                    alternations += 1

            if total_possible > 0:
                wave_scores.append(alternations / total_possible)

        if not wave_scores:
            return {'confidence': 0.0, 'details': 'No valid data'}

        confidence = statistics.mean(wave_scores)
        return {
            'confidence': confidence,
            'details': f'Wave pattern frequency: {confidence:.2f}',
            'sample_workouts': len(wave_scores)
        }

    def _analyze_cluster_pattern(self, workout_history: List[Dict]) -> Dict[str, Any]:
        """Analyze cluster sets pattern (groups of same weight)"""
        cluster_scores = []

        for workout in workout_history:
            sets = workout.get('sets', [])
            if len(sets) < 3:
                continue

            weights = [s['weight'] for s in sets]
            clusters = 0
            i = 0

            while i < len(weights):
                cluster_size = 1
                current_weight = weights[i]

                # Count consecutive sets with same weight
                while (i + cluster_size < len(weights) and
                       abs(weights[i + cluster_size] - current_weight) <= self.pattern_config['weight_change_threshold']):
                    cluster_size += 1

                if cluster_size >= 2:  # At least 2 sets to be a cluster
                    clusters += 1

                i += cluster_size

            # Score based on number of clusters relative to total sets
            cluster_scores.append(min(clusters / (len(sets) / 2), 1.0))

        if not cluster_scores:
            return {'confidence': 0.0, 'details': 'No valid data'}

        confidence = statistics.mean(cluster_scores)
        return {
            'confidence': confidence,
            'details': f'Cluster pattern frequency: {confidence:.2f}',
            'sample_workouts': len(cluster_scores)
        }

    def _calculate_pattern_consistency(self, workout_history: List[Dict], pattern_type: PatternType) -> float:
        """Calculate how consistently a pattern appears across workouts"""
        if not workout_history:
            return 0.0

        consistent_workouts = 0

        for workout in workout_history:
            sets = workout.get('sets', [])
            if len(sets) < 2:
                continue

            # Check if this workout follows the pattern
            if self._workout_matches_pattern(sets, pattern_type):
                consistent_workouts += 1

        return consistent_workouts / len(workout_history) if workout_history else 0.0

    def _workout_matches_pattern(self, sets: List[Dict], pattern_type: PatternType) -> bool:
        """Check if a single workout matches the given pattern"""
        if len(sets) < 2:
            return False

        weights = [s['weight'] for s in sets]

        if pattern_type == PatternType.ASCENDING:
            return all(weights[i+1] >= weights[i] for i in range(len(weights)-1))
        elif pattern_type == PatternType.DESCENDING:
            return all(weights[i+1] <= weights[i] for i in range(len(weights)-1))
        elif pattern_type == PatternType.STRAIGHT:
            return all(abs(weights[i+1] - weights[i]) <= self.pattern_config['weight_change_threshold']
                      for i in range(len(weights)-1))
        # Add more pattern checks as needed

        return False

    def _analyze_trend_direction(self, workout_history: List[Dict]) -> str:
        """Analyze overall trend direction across workouts"""
        if len(workout_history) < 2:
            return 'unknown'

        # Calculate average weight per workout
        workout_averages = []
        for workout in workout_history:
            sets = workout.get('sets', [])
            if sets:
                avg_weight = statistics.mean([s['weight'] for s in sets])
                workout_averages.append(avg_weight)

        if len(workout_averages) < 2:
            return 'unknown'

        # Simple linear trend analysis
        first_half = workout_averages[:len(workout_averages)//2]
        second_half = workout_averages[len(workout_averages)//2:]

        first_avg = statistics.mean(first_half)
        second_avg = statistics.mean(second_half)

        change_percent = ((second_avg - first_avg) / first_avg) * 100 if first_avg > 0 else 0

        if change_percent > 5:
            return 'increasing'
        elif change_percent < -5:
            return 'decreasing'
        else:
            return 'stable'

    def _generate_pattern_recommendation(self, pattern_type: PatternType, pattern_data: Dict,
                                       consistency_score: float, trend_direction: str) -> str:
        """Generate recommendations based on pattern analysis"""
        recommendations = []

        if consistency_score >= 0.8:
            recommendations.append(f"Excellent pattern consistency ({consistency_score:.1%})")
        elif consistency_score >= 0.6:
            recommendations.append(f"Good pattern consistency ({consistency_score:.1%})")
        else:
            recommendations.append(f"Consider improving pattern consistency ({consistency_score:.1%})")

        if pattern_type == PatternType.ASCENDING:
            recommendations.append("Pyramid training is excellent for strength building")
        elif pattern_type == PatternType.STRAIGHT:
            recommendations.append("Straight sets are ideal for volume and consistency")
        elif pattern_type == PatternType.DESCENDING:
            recommendations.append("Reverse pyramid is great for high-intensity training")

        if trend_direction == 'increasing':
            recommendations.append("Progressive overload is working well")
        elif trend_direction == 'decreasing':
            recommendations.append("Consider reviewing your progression strategy")

        return ". ".join(recommendations)

    # Multi-factor readiness calculation methods

    def _calculate_rep_achievement_score(self, recent_workouts: List[Dict]) -> float:
        """Calculate score based on rep achievement relative to targets"""
        if not recent_workouts:
            return 0.0

        achievement_scores = []

        for workout in recent_workouts:
            sets = workout.get('sets', [])
            if not sets:
                continue

            # Get target reps (assume from user preferences or exercise defaults)
            target_reps = self._get_target_reps(workout.get('exercise_id'))

            total_reps = sum(s['reps'] for s in sets)
            target_total = target_reps * len(sets)

            if target_total > 0:
                achievement_scores.append(min(total_reps / target_total, 1.0))

        return statistics.mean(achievement_scores) if achievement_scores else 0.0

    def _calculate_workout_consistency(self, recent_workouts: List[Dict]) -> float:
        """Calculate consistency score based on workout frequency and performance"""
        if len(recent_workouts) < 2:
            return 0.0

        # Check workout frequency consistency
        dates = [datetime.fromisoformat(w['date']) for w in recent_workouts]
        dates.sort()

        intervals = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]

        if not intervals:
            return 0.0

        # Ideal interval is 2-4 days
        ideal_interval = 3
        consistency_scores = []

        for interval in intervals:
            if 2 <= interval <= 4:
                consistency_scores.append(1.0)
            elif 1 <= interval <= 6:
                consistency_scores.append(0.7)
            else:
                consistency_scores.append(0.3)

        return statistics.mean(consistency_scores)

    def _calculate_time_factor_score(self, user_id: int, exercise_id: int) -> float:
        """Calculate score based on time since last progression"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT progression_date
                    FROM progression_history
                    WHERE user_id = ? AND exercise_id = ?
                    ORDER BY progression_date DESC
                    LIMIT 1
                """, (user_id, exercise_id))

                result = cursor.fetchone()

                if not result:
                    # No previous progressions - moderate score
                    return 0.6

                last_progression = datetime.fromisoformat(result[0])
                days_since = (datetime.now() - last_progression).days

                # Optimal progression frequency is 1-2 weeks
                if 7 <= days_since <= 14:
                    return 1.0
                elif 3 <= days_since <= 21:
                    return 0.8
                elif days_since <= 28:
                    return 0.6
                else:
                    return 0.4  # Too long since last progression

        except Exception as e:
            self.logger.error(f"Error calculating time factor: {e}")
            return 0.5

    def _calculate_volume_trend_score(self, recent_workouts: List[Dict]) -> float:
        """Calculate score based on volume trend"""
        if len(recent_workouts) < 2:
            return 0.5

        volumes = []
        for workout in recent_workouts:
            sets = workout.get('sets', [])
            volume = sum(s['weight'] * s['reps'] for s in sets)
            volumes.append(volume)

        if len(volumes) < 2:
            return 0.5

        # Calculate trend
        first_half = volumes[:len(volumes)//2]
        second_half = volumes[len(volumes)//2:]

        first_avg = statistics.mean(first_half)
        second_avg = statistics.mean(second_half)

        if first_avg == 0:
            return 0.5

        change_percent = ((second_avg - first_avg) / first_avg) * 100

        if change_percent > 10:
            return 1.0  # Strong positive trend
        elif change_percent > 0:
            return 0.8  # Positive trend
        elif change_percent > -5:
            return 0.6  # Stable
        else:
            return 0.3  # Declining trend

    def _calculate_form_quality_score(self, recent_workouts: List[Dict]) -> float:
        """Calculate score based on form quality if tracked"""
        form_scores = []

        for workout in recent_workouts:
            sets = workout.get('sets', [])
            for set_data in sets:
                if 'form_quality' in set_data and set_data['form_quality'] is not None:
                    # Assuming form_quality is 1-5 scale
                    form_scores.append(set_data['form_quality'] / 5.0)

        return statistics.mean(form_scores) if form_scores else 0.0

    # Helper methods for data retrieval

    def _get_workout_history(self, user_id: int, exercise_id: int, limit: int) -> List[Dict]:
        """Get workout history with sets data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT ws.id, ws.date, ws.exercise_id,
                           wset.weight, wset.reps, wset.set_number, wset.rpe, wset.form_quality
                    FROM workout_sessions ws
                    JOIN workout_sets wset ON ws.id = wset.session_id
                    WHERE ws.user_id = ? AND ws.exercise_id = ? AND ws.status = 'completed'
                    ORDER BY ws.date DESC
                    LIMIT ?
                """, (user_id, exercise_id, limit * 10))  # Get more sets to group by workout

                rows = cursor.fetchall()

                # Group sets by workout session
                workouts = {}
                for row in rows:
                    session_id, date, ex_id, weight, reps, set_num, rpe, form_quality = row

                    if session_id not in workouts:
                        workouts[session_id] = {
                            'session_id': session_id,
                            'date': date,
                            'exercise_id': ex_id,
                            'sets': []
                        }

                    workouts[session_id]['sets'].append({
                        'weight': weight,
                        'reps': reps,
                        'set_number': set_num,
                        'rpe': rpe,
                        'form_quality': form_quality
                    })

                # Sort sets within each workout and return limited workouts
                workout_list = list(workouts.values())
                for workout in workout_list:
                    workout['sets'].sort(key=lambda x: x['set_number'])

                return workout_list[:limit]

        except Exception as e:
            self.logger.error(f"Error getting workout history: {e}")
            return []

    def _get_current_performance(self, user_id: int, exercise_id: int) -> Optional[Dict]:
        """Get current performance metrics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT MAX(weight) as max_weight, MAX(reps) as max_reps,
                           AVG(weight) as avg_weight, AVG(reps) as avg_reps
                    FROM workout_sets ws
                    JOIN workout_sessions wss ON ws.session_id = wss.id
                    WHERE wss.user_id = ? AND wss.exercise_id = ? AND wss.status = 'completed'
                    AND wss.date >= date('now', '-30 days')
                """, (user_id, exercise_id))

                result = cursor.fetchone()

                if result and result[0]:
                    return {
                        'max_weight': result[0],
                        'max_reps': result[1],
                        'avg_weight': result[2],
                        'avg_reps': result[3]
                    }

                return None

        except Exception as e:
            self.logger.error(f"Error getting current performance: {e}")
            return None

    def _get_progression_history(self, user_id: int, exercise_id: int) -> List[Dict]:
        """Get progression history"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT progression_date, progression_type, old_value, new_value, notes
                    FROM progression_history
                    WHERE user_id = ? AND exercise_id = ?
                    ORDER BY progression_date DESC
                    LIMIT 10
                """, (user_id, exercise_id))

                rows = cursor.fetchall()

                return [{
                    'date': row[0],
                    'type': row[1],
                    'old_value': row[2],
                    'new_value': row[3],
                    'notes': row[4]
                } for row in rows]

        except Exception as e:
            self.logger.error(f"Error getting progression history: {e}")
            return []

    def _get_target_reps(self, exercise_id: int) -> int:
        """Get target reps for exercise (placeholder - implement based on user preferences)"""
        # This would typically come from user preferences or exercise defaults
        return 12  # Default target

    # Smart suggestion generation methods

    def _generate_weight_increase_suggestion(self, current_performance: Dict, readiness: ReadinessFactors,
                                           pattern_analysis: PatternAnalysis, progression_history: List[Dict]) -> Optional[SmartSuggestion]:
        """Generate weight increase suggestion"""
        if not current_performance:
            return None

        current_weight = current_performance['max_weight']

        # Determine increment based on user level and exercise
        if self._is_advanced_user(progression_history):
            increment = self.pattern_config['microloading_threshold']  # 1.25kg for advanced
        else:
            increment = 2.5  # Standard increment

        suggested_weight = current_weight + increment

        reasoning_parts = [
            f"High readiness score ({readiness.overall_readiness:.1%})",
            f"Consistent {pattern_analysis.pattern.value} pattern",
            f"Good rep achievement ({readiness.rep_achievement_score:.1%})"
        ]

        alternatives = [
            {
                'type': 'conservative',
                'value': current_weight + (increment / 2),
                'description': 'Smaller increment for safety'
            },
            {
                'type': 'aggressive',
                'value': current_weight + (increment * 1.5),
                'description': 'Larger increment if feeling strong'
            }
        ]

        return SmartSuggestion(
            suggestion_type='weight_increase',
            current_value=current_weight,
            suggested_value=suggested_weight,
            confidence=readiness.overall_readiness,
            reasoning='. '.join(reasoning_parts),
            alternative_options=alternatives
        )

    def _generate_rep_increase_suggestion(self, current_performance: Dict, readiness: ReadinessFactors,
                                        pattern_analysis: PatternAnalysis) -> Optional[SmartSuggestion]:
        """Generate rep increase suggestion"""
        if not current_performance:
            return None

        current_reps = current_performance['max_reps']
        suggested_reps = current_reps + 1

        reasoning_parts = [
            f"Moderate readiness ({readiness.overall_readiness:.1%})",
            "Focus on rep progression before weight increase",
            f"Current pattern: {pattern_analysis.pattern.value}"
        ]

        alternatives = [
            {
                'type': 'volume',
                'value': current_reps,
                'description': 'Add an extra set instead'
            }
        ]

        return SmartSuggestion(
            suggestion_type='rep_increase',
            current_value=current_reps,
            suggested_value=suggested_reps,
            confidence=readiness.overall_readiness,
            reasoning='. '.join(reasoning_parts),
            alternative_options=alternatives
        )

    def _generate_deload_suggestion(self, current_performance: Dict, progression_history: List[Dict]) -> Optional[SmartSuggestion]:
        """Generate deload suggestion"""
        if not current_performance:
            return None

        current_weight = current_performance['max_weight']
        deload_weight = current_weight * 0.85  # 15% reduction

        reasoning = "Multiple failed progressions detected. Deload recommended for recovery and technique focus."

        alternatives = [
            {
                'type': 'light_deload',
                'value': current_weight * 0.9,
                'description': '10% reduction - lighter deload'
            },
            {
                'type': 'heavy_deload',
                'value': current_weight * 0.8,
                'description': '20% reduction - more aggressive deload'
            }
        ]

        return SmartSuggestion(
            suggestion_type='deload',
            current_value=current_weight,
            suggested_value=deload_weight,
            confidence=0.8,
            reasoning=reasoning,
            alternative_options=alternatives
        )

    def _generate_plateau_break_suggestion(self, current_performance: Dict, pattern_analysis: PatternAnalysis,
                                         progression_history: List[Dict]) -> Optional[SmartSuggestion]:
        """Generate plateau breaking suggestion"""
        if not current_performance:
            return None

        current_weight = current_performance['max_weight']

        # Suggest pattern change or technique variation
        if pattern_analysis.pattern == PatternType.STRAIGHT:
            suggestion = "Try pyramid training"
            new_approach = "ascending"
        else:
            suggestion = "Try straight sets"
            new_approach = "straight"

        reasoning = f"Plateau detected after {len(progression_history)} weeks. Pattern change recommended."

        alternatives = [
            {
                'type': 'rep_range_change',
                'value': current_weight * 0.9,
                'description': 'Lower weight, higher reps (15-20 range)'
            },
            {
                'type': 'frequency_change',
                'value': current_weight,
                'description': 'Increase training frequency'
            }
        ]

        return SmartSuggestion(
            suggestion_type='plateau_break',
            current_value=current_weight,
            suggested_value=current_weight,  # Same weight, different approach
            confidence=0.7,
            reasoning=reasoning,
            alternative_options=alternatives
        )

    def _should_suggest_deload(self, progression_history: List[Dict], readiness: ReadinessFactors) -> bool:
        """Determine if deload should be suggested"""
        if len(progression_history) < 3:
            return False

        # Check for multiple failed progressions
        recent_progressions = progression_history[:3]
        failed_progressions = sum(1 for p in recent_progressions if 'failed' in p.get('notes', '').lower())

        return failed_progressions >= 2 or readiness.overall_readiness < 0.3

    def _detect_plateau(self, progression_history: List[Dict]) -> bool:
        """Detect if user is in a plateau"""
        if len(progression_history) < 4:
            return False

        # Check if no progressions in last 4 weeks
        recent_dates = [datetime.fromisoformat(p['date']) for p in progression_history[:4]]
        oldest_recent = min(recent_dates)

        return (datetime.now() - oldest_recent).days > 28

    def _is_advanced_user(self, progression_history: List[Dict]) -> bool:
        """Determine if user is advanced based on progression history"""
        return len(progression_history) > 10

    def _generate_readiness_recommendation(self, overall_readiness: float, factor_scores: Dict) -> str:
        """Generate recommendation based on readiness factors"""
        if overall_readiness >= 0.8:
            return "Ready for progression - consider increasing weight"
        elif overall_readiness >= 0.6:
            return "Close to progression - focus on consistency for 1-2 more workouts"
        elif overall_readiness >= 0.4:
            return "Building strength - maintain current intensity and focus on form"
        else:
            return "Consider deload or technique work - readiness factors are low"
