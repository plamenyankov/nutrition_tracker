"""
Readiness Analyzer - analyzes progression readiness for exercises
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import statistics
import logging
from ..calculators.weight_calculator import WeightCalculator

logger = logging.getLogger(__name__)


class ReadinessAnalyzer:
    """Analyzes readiness for progression based on multiple factors"""

    def analyze_set_progression(self, set_history: List[Dict], user_prefs: Dict,
                              exercise_info: Dict, is_upper_body: bool) -> Dict:
        """Analyze progression readiness for a specific set"""
        if len(set_history) < 2:
            # If we have at least one history entry, suggest improving on it
            if set_history:
                last_performance = set_history[0]
                return {
                    'ready': False,
                    'confidence': 0.0,
                    'suggestion': 'build_strength',
                    'current_weight': last_performance['weight'],
                    'current_avg_reps': last_performance['reps'],
                    'suggested_reps': last_performance['reps'] + 1,
                    'reps_to_go': max(1, user_prefs['max_reps_target'] - last_performance['reps']),
                    'target_reps': user_prefs['max_reps_target']
                }
            else:
                return {
                    'ready': False,
                    'confidence': 0.0,
                    'suggestion': 'Need more workout history',
                    'suggested_reps': user_prefs['min_reps_target'],
                    'reps_to_go': None
                }

        # Get rep targets from preferences
        min_reps = user_prefs.get('min_reps_target', 10)
        max_reps = user_prefs.get('max_reps_target', 15)
        # Always use 5kg increment
        weight_increment = 5.0

        # Analyze recent performance
        recent_weights = [h['weight'] for h in set_history[:3]]
        recent_reps = [h['reps'] for h in set_history[:3]]

        current_weight = recent_weights[0]
        current_reps = recent_reps[0]

        # Check if user recently progressed in weight
        recently_progressed = self._check_recent_progression(set_history)

        # Find best performance at current weight
        best_reps_at_weight = self._get_best_reps_at_weight(set_history, current_weight)

        if recently_progressed:
            return self._analyze_after_recent_progression(
                current_weight, current_reps, best_reps_at_weight,
                min_reps, max_reps, weight_increment
            )
        else:
            return self._analyze_standard_progression(
                recent_weights, recent_reps, current_weight, best_reps_at_weight,
                min_reps, max_reps, weight_increment
            )

    def _check_recent_progression(self, history: List[Dict]) -> bool:
        """Check if user recently progressed in weight"""
        if len(history) < 2:
            return False

        current_weight = history[0]['weight']

        # Check last 4 workouts for weight changes
        for i in range(1, min(len(history), 4)):
            if history[i]['weight'] < current_weight:
                return True

        # Check if current weight is higher than oldest in sample
        if len(history) >= 3:
            oldest_weight = history[-1]['weight']
            if current_weight > oldest_weight:
                return True

        return False

    def _get_best_reps_at_weight(self, history: List[Dict], weight: float) -> int:
        """Find best rep performance at a specific weight"""
        reps_at_weight = [h['reps'] for h in history if h['weight'] == weight]
        return max(reps_at_weight) if reps_at_weight else 0

    def _analyze_after_recent_progression(self, current_weight: float, current_reps: int,
                                        best_reps_at_weight: int, min_reps: int, max_reps: int,
                                        weight_increment: float) -> Dict:
        """Analyze readiness after recent weight progression"""
        if current_reps >= max_reps:
            # Already hitting max reps with new weight - ready for another progression!
            new_weight = current_weight + weight_increment
            # Calculate volume-based reps for the new weight
            suggested_reps = WeightCalculator.calculate_volume_based_reps(
                current_weight, current_reps, new_weight
            )
            return {
                'ready': True,
                'confidence': 0.95,
                'suggestion': 'increase_weight',
                'current_weight': current_weight,
                'suggested_weight': new_weight,
                'suggested_reps': suggested_reps,
                'reps_to_go': 0,
                'target_reps': max_reps
            }
        elif current_reps >= min_reps:
            # Adapting well to new weight
            suggested_reps = max(current_reps + 1, best_reps_at_weight)
            return {
                'ready': False,
                'confidence': 0.7,
                'suggestion': 'build_strength',
                'current_weight': current_weight,
                'current_avg_reps': current_reps,
                'suggested_reps': suggested_reps,
                'reps_to_go': max(1, max_reps - current_reps),
                'target_reps': max_reps
            }
        else:
            # Struggling with new weight
            suggested_reps = max(current_reps + 1, best_reps_at_weight, min_reps)
            return {
                'ready': False,
                'confidence': 0.4,
                'suggestion': 'build_reps',
                'current_weight': current_weight,
                'current_avg_reps': current_reps,
                'suggested_reps': suggested_reps,
                'reps_to_go': max(1, min_reps - current_reps),
                'target_reps': min_reps
            }

    def _analyze_standard_progression(self, recent_weights: List[float], recent_reps: List[int],
                                    current_weight: float, best_reps_at_weight: int,
                                    min_reps: int, max_reps: int, weight_increment: float) -> Dict:
        """Analyze standard progression readiness"""
        # Check if consistently hitting max reps
        hitting_max_reps = all(r >= max_reps for r in recent_reps[:2])
        avg_reps = statistics.mean(recent_reps[:2])

        if hitting_max_reps:
            # Ready to progress in weight
            new_weight = current_weight + weight_increment
            # Calculate volume-based reps using the best recent performance
            best_recent_reps = max(recent_reps[:2])
            suggested_reps = WeightCalculator.calculate_volume_based_reps(
                current_weight, best_recent_reps, new_weight
            )
            return {
                'ready': True,
                'confidence': 0.9,
                'suggestion': 'increase_weight',
                'current_weight': current_weight,
                'suggested_weight': new_weight,
                'suggested_reps': suggested_reps,
                'reps_to_go': 0,
                'target_reps': max_reps
            }
        elif avg_reps >= max_reps - 1:
            # Close to progression
            suggested_reps = max(int(avg_reps) + 1, best_reps_at_weight)
            return {
                'ready': False,
                'confidence': 0.6,
                'suggestion': 'almost_ready',
                'current_weight': current_weight,
                'suggested_reps': suggested_reps,
                'reps_to_go': max(1, int(max_reps - avg_reps)),
                'target_reps': max_reps
            }
        else:
            # Focus on increasing reps
            suggested_reps = max(int(avg_reps) + 1, best_reps_at_weight)
            return {
                'ready': False,
                'confidence': 0.3,
                'suggestion': 'increase_reps',
                'current_weight': current_weight,
                'current_avg_reps': round(avg_reps, 1),
                'suggested_reps': suggested_reps,
                'reps_to_go': int(max_reps - avg_reps),
                'target_reps': max_reps
            }

    def analyze_volume_readiness(self, volume_data: List[Dict]) -> Dict:
        """Analyze readiness based on volume trends"""
        if len(volume_data) < 2:
            return {
                'trend': 'insufficient_data',
                'readiness_score': 0.5,
                'recommendation': 'Need more data'
            }

        # Calculate trend
        first_half = volume_data[:len(volume_data)//2]
        second_half = volume_data[len(volume_data)//2:]

        first_avg = statistics.mean([d['total_volume'] for d in first_half])
        second_avg = statistics.mean([d['total_volume'] for d in second_half])

        if first_avg == 0:
            return {
                'trend': 'no_volume',
                'readiness_score': 0,
                'recommendation': 'Start tracking workouts'
            }

        change_percent = ((second_avg - first_avg) / first_avg) * 100

        if change_percent > 10:
            return {
                'trend': 'increasing',
                'readiness_score': 1.0,
                'recommendation': 'Strong positive trend - ready for progression',
                'volume_change': round(change_percent, 1)
            }
        elif change_percent > 0:
            return {
                'trend': 'stable_positive',
                'readiness_score': 0.8,
                'recommendation': 'Positive trend - close to progression',
                'volume_change': round(change_percent, 1)
            }
        elif change_percent > -5:
            return {
                'trend': 'stable',
                'readiness_score': 0.6,
                'recommendation': 'Stable performance - maintain current load',
                'volume_change': round(change_percent, 1)
            }
        else:
            return {
                'trend': 'declining',
                'readiness_score': 0.3,
                'recommendation': 'Declining trend - consider deload',
                'volume_change': round(change_percent, 1)
            }
