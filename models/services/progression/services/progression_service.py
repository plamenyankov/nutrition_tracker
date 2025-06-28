"""
Simplified Progression Service - main interface for progression functionality
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

from ..base import BaseProgressionService
from ..repositories.workout_repository import WorkoutRepository
from ..repositories.progression_repository import ProgressionRepository
from ..analyzers.pattern_analyzer import PatternAnalyzer
from ..analyzers.readiness_analyzer import ReadinessAnalyzer
from ..calculators.weight_calculator import WeightCalculator

logger = logging.getLogger(__name__)


class ProgressionService(BaseProgressionService):
    """Main service for progression analysis and suggestions"""

    def __init__(self, user_id: Optional[int] = None, connection_manager=None):
        super().__init__(user_id, connection_manager)

        # Initialize repositories
        self.workout_repo = WorkoutRepository(user_id, connection_manager)
        self.progression_repo = ProgressionRepository(user_id, connection_manager)

        # Initialize analyzers
        self.pattern_analyzer = PatternAnalyzer()
        self.readiness_analyzer = ReadinessAnalyzer()

        # Initialize calculators
        self.weight_calculator = WeightCalculator()

    def analyze_set_progression(self, exercise_id: int, set_number: int) -> Dict:
        """Analyze progression readiness for a specific set"""
        if not self.validate_user_id() or not self.validate_exercise_id(exercise_id):
            return {'ready': False, 'error': 'Invalid user or exercise ID'}

        # Get user preferences
        prefs = self.get_user_preferences()

        # Get exercise info
        exercise_info = self.workout_repo.get_exercise_info(exercise_id)
        if not exercise_info:
            return {'ready': False, 'error': 'Exercise not found'}

        # Determine if upper body
        is_upper_body = self.weight_calculator.is_upper_body_exercise(exercise_info)

        # Get set history
        if self.user_id is None:
            return {'ready': False, 'error': 'User ID not set'}

        set_history = self.workout_repo.get_set_history(self.user_id, exercise_id, set_number)

        # Analyze readiness
        return self.readiness_analyzer.analyze_set_progression(
            set_history, prefs, exercise_info, is_upper_body
        )

    def get_pattern_analysis(self, exercise_id: int) -> Dict:
        """Get pattern analysis for an exercise"""
        if not self.validate_user_id() or not self.validate_exercise_id(exercise_id):
            return {'pattern': 'unknown', 'error': 'Invalid user or exercise ID'}

        if self.user_id is None:
            return {'pattern': 'unknown', 'error': 'User ID not set'}

        # Get recent workouts
        workouts = self.workout_repo.get_recent_workouts(self.user_id, exercise_id, days=30)

        # Analyze pattern
        pattern_result = self.pattern_analyzer.detect_pattern(workouts)

        # Add set consistency analysis
        consistency = self.pattern_analyzer.analyze_set_consistency(workouts)
        pattern_result['set_consistency'] = consistency

        return pattern_result

    def get_volume_trend(self, exercise_id: int, days: int = 30) -> Dict:
        """Get volume trend analysis for an exercise"""
        if not self.validate_user_id() or not self.validate_exercise_id(exercise_id):
            return {'trend': 'error', 'error': 'Invalid user or exercise ID'}

        if self.user_id is None:
            return {'trend': 'error', 'error': 'User ID not set'}

        # Get volume data
        volume_data = self.workout_repo.get_volume_data(self.user_id, exercise_id, days)

        # Analyze volume readiness
        return self.readiness_analyzer.analyze_volume_readiness(volume_data)

    def suggest_set_addition(self, exercise_id: int) -> Dict:
        """Suggest when to add a new set to an exercise"""
        if not self.validate_user_id() or not self.validate_exercise_id(exercise_id):
            return {'suggest_add_set': False, 'error': 'Invalid user or exercise ID'}

        if self.user_id is None:
            return {'suggest_add_set': False, 'error': 'User ID not set'}

        # Get recent workouts
        workouts = self.workout_repo.get_recent_workouts(self.user_id, exercise_id, days=30, limit=3)

        if not workouts:
            return {'suggest_add_set': False, 'reason': 'No recent workout data'}

        # Get current typical set count
        set_counts = [len(w['sets']) for w in workouts]
        current_sets = max(set_counts) if set_counts else 0

        if current_sets == 0:
            return {'suggest_add_set': False, 'reason': 'No sets found'}

        # Check performance on current last set
        last_set_history = self.workout_repo.get_set_history(self.user_id, exercise_id, current_sets, limit=3)

        if len(last_set_history) < 3:
            return {'suggest_add_set': False, 'reason': 'Not enough history on current sets'}

        # Get user preferences
        prefs = self.get_user_preferences()
        min_reps = prefs.get('min_reps_target', 10)

        # Check if consistently performing well on last set
        last_set_reps = [h['reps'] for h in last_set_history[:3]]
        avg_last_set_reps = sum(last_set_reps) / len(last_set_reps)

        # Suggest new set if:
        # 1. Consistently hitting good reps on last set (>= min_reps)
        # 2. Has been doing current set count for at least 3 workouts
        # 3. Not already at 6+ sets (diminishing returns)

        if (avg_last_set_reps >= min_reps and
            all(c == current_sets for c in set_counts[:3]) and
            current_sets < 6):

            # Get pattern info
            pattern_info = self.get_pattern_analysis(exercise_id)

            # Calculate suggested weight for new set
            last_weight = last_set_history[0]['weight']
            exercise_info = self.workout_repo.get_exercise_info(exercise_id) or {}
            is_upper_body = self.weight_calculator.is_upper_body_exercise(exercise_info)

            if pattern_info['pattern'] == 'ascending':
                # Always use 5kg increment
                increment = 5.0
                suggested_weight = last_weight + increment
            elif pattern_info['pattern'] == 'descending':
                # Decrease weight from last set
                suggested_weight = max(20, last_weight - 5.0)
            else:
                # Same weight as last set
                suggested_weight = last_weight

            return {
                'suggest_add_set': True,
                'reason': f'Consistently performing well on set {current_sets}',
                'current_sets': current_sets,
                'new_set_number': current_sets + 1,
                'suggested_weight': suggested_weight,
                'suggested_reps': 6,  # Start conservative with new set
                'pattern': pattern_info['pattern']
            }

        return {
            'suggest_add_set': False,
            'reason': f'Focus on current {current_sets} sets',
            'current_performance': f'Averaging {avg_last_set_reps:.1f} reps on last set'
        }

    def get_user_preferences(self) -> Dict:
        """Get user preferences with defaults"""
        if not self.validate_user_id():
            return self._get_default_preferences()

        if self.user_id is None:
            return self._get_default_preferences()

        prefs = self.progression_repo.get_user_preferences(self.user_id)
        return prefs or self._get_default_preferences()

    def update_user_preferences(self, preferences: Dict) -> bool:
        """Update user preferences"""
        if not self.validate_user_id():
            return False

        if self.user_id is None:
            return False

        return self.progression_repo.update_user_preferences(self.user_id, preferences)

    def record_progression(self, exercise_id: int, old_weight: float, new_weight: float,
                         progression_type: str = 'weight_increase', notes: str = '') -> bool:
        """Record a progression event"""
        if not self.validate_user_id() or not self.validate_exercise_id(exercise_id):
            return False

        if self.user_id is None:
            return False

        # Validate progression data
        if old_weight <= 0 or new_weight <= 0 or new_weight <= old_weight:
            logger.error(f"Invalid progression data: {old_weight}kg -> {new_weight}kg")
            return False

        return self.progression_repo.record_progression(
            self.user_id, exercise_id, old_weight, new_weight, progression_type, notes
        )

    def record_set_progression(self, exercise_id: int, set_number: int,
                             old_weight: float, new_weight: float, old_reps: int,
                             new_reps: int, progression_type: str, notes: str = '') -> bool:
        """Record a set-specific progression event"""
        if not self.validate_user_id() or not self.validate_exercise_id(exercise_id):
            return False

        if self.user_id is None:
            return False

        return self.progression_repo.record_set_progression(
            self.user_id, exercise_id, set_number, old_weight, new_weight,
            old_reps, new_reps, progression_type, notes
        )

    def calculate_volume_metrics(self, workout_id: int, exercise_id: int) -> Dict:
        """Calculate and store volume metrics for a workout"""
        return self.progression_repo.calculate_and_store_volume_metrics(workout_id, exercise_id)

    def _get_default_preferences(self) -> Dict:
        """Return default preferences"""
        return {
            'progression_strategy': 'reps_first',
            'min_reps_target': 10,
            'max_reps_target': 15,
            'weight_increment_upper': 2.5,
            'weight_increment_lower': 5.0,
            'rest_timer_enabled': True,
            'progression_notification_enabled': True,
            'pyramid_preference': 'auto_detect'
        }
