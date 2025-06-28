"""
Progression Service Adapter - provides backward compatibility with old API
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import statistics
import logging

from models.services.progression import ProgressionService as NewProgressionService
from models.services.progression.repositories.workout_repository import WorkoutRepository
from models.services.progression.repositories.progression_repository import ProgressionRepository
from models.services.progression.analyzers.pattern_analyzer import PatternAnalyzer
from models.services.progression.analyzers.readiness_analyzer import ReadinessAnalyzer
from models.services.progression.calculators.weight_calculator import WeightCalculator

logger = logging.getLogger(__name__)


class ProgressionService:
    """Adapter class providing backward compatibility with old ProgressionService API"""

    def __init__(self, user_id: Optional[int] = None, connection_manager=None):
        self.user_id = user_id
        self.new_service = NewProgressionService(user_id, connection_manager)
        self.workout_repo = WorkoutRepository(user_id, connection_manager)
        self.progression_repo = ProgressionRepository(user_id, connection_manager)
        self.pattern_analyzer = PatternAnalyzer()
        self.readiness_analyzer = ReadinessAnalyzer()
        self.weight_calculator = WeightCalculator()

    def get_user_preferences(self, user_id: int) -> Dict:
        """Get user preferences"""
        self.new_service.set_user_id(user_id)
        return self.new_service.get_user_preferences()

    def update_user_preferences(self, user_id: int, preferences: Dict) -> bool:
        """Update user preferences"""
        self.new_service.set_user_id(user_id)
        return self.new_service.update_user_preferences(preferences)

    def check_progression_readiness(self, user_id: int, exercise_id: int) -> Dict:
        """Check progression readiness - backward compatible method"""
        self.new_service.set_user_id(user_id)

        # Get user preferences
        prefs = self.new_service.get_user_preferences()

        # Get recent workouts
        workouts = self.workout_repo.get_recent_workouts(user_id, exercise_id, days=30, limit=5)

        if len(workouts) < 2:
            return {
                'ready': False,
                'reason': 'Need at least 2 completed workouts for this exercise',
                'suggestion': 'complete_more_workouts',
                'confidence': 0.0,
                'workouts_needed': 2 - len(workouts)
            }

        # Get exercise info
        exercise_info = self.workout_repo.get_exercise_info(exercise_id)
        if not exercise_info:
            return {
                'ready': False,
                'reason': 'Exercise information not found',
                'suggestion': 'check_exercise_data',
                'confidence': 0.0
            }

        # Analyze using the most recent sets
        is_upper_body = self.weight_calculator.is_upper_body_exercise(exercise_info)

        # Get performance stats
        stats = self.workout_repo.get_exercise_performance_stats(user_id, exercise_id, days=30)

        if not stats:
            return {
                'ready': False,
                'reason': 'No performance data available',
                'suggestion': 'complete_more_workouts',
                'confidence': 0.0
            }

        # Simple readiness check based on recent performance
        max_reps_target = prefs.get('max_reps_target', 15)

        # Check if consistently hitting max reps
        ready = stats.get('avg_reps', 0) >= max_reps_target - 1

        if ready:
            # Always use 5kg increment
            weight_increment = 5.0
            current_weight = stats.get('max_weight', 0)
            new_weight = current_weight + weight_increment

            # Calculate volume-based reps
            from models.services.progression.calculators.weight_calculator import WeightCalculator
            current_reps = stats.get('max_reps', max_reps_target)
            suggested_reps = WeightCalculator.calculate_volume_based_reps(
                current_weight, current_reps, new_weight
            )

            return {
                'ready': True,
                'suggestion': 'increase_weight',
                'current_weight': current_weight,
                'new_weight': new_weight,
                'new_reps_target': suggested_reps,
                'reason': f'Consistently hitting {max_reps_target} reps',
                'confidence': 0.9
            }
        else:
            return {
                'ready': False,
                'suggestion': 'increase_reps',
                'current_avg_reps': round(stats.get('avg_reps', 0), 1),
                'target_reps': max_reps_target,
                'reps_to_go': round(max_reps_target - stats.get('avg_reps', 0), 1),
                'reason': f'Average {stats.get("avg_reps", 0):.1f} reps, need {max_reps_target}',
                'confidence': stats.get('avg_reps', 0) / max_reps_target if max_reps_target > 0 else 0
            }

    def _get_exercise_info(self, exercise_id: int) -> Dict:
        """Get exercise info - backward compatible method"""
        return self.workout_repo.get_exercise_info(exercise_id) or {}

    def get_exercise_performance_history(self, user_id: int, exercise_id: int, limit: int = 5) -> List[Dict]:
        """Get exercise performance history - backward compatible method"""
        workouts = self.workout_repo.get_recent_workouts(user_id, exercise_id, days=90, limit=limit)

        history = []
        for workout in workouts:
            if workout.get('sets'):
                # Aggregate workout data
                weights = [s['weight'] for s in workout['sets'] if s.get('weight')]
                reps = [s['reps'] for s in workout['sets'] if s.get('reps')]

                if weights and reps:
                    history.append({
                        'workout_id': workout.get('session_id'),
                        'date': workout.get('date'),
                        'sets': workout['sets'],
                        'max_weight': max(weights),
                        'avg_weight': sum(weights) / len(weights),
                        'max_reps': max(reps),
                        'avg_reps': sum(reps) / len(reps),
                        'total_sets': len(workout['sets'])
                    })

        return history

    def get_exercise_trend(self, user_id: int, exercise_id: int, days: int = 30) -> Dict:
        """Get exercise trend - backward compatible method"""
        volume_data = self.workout_repo.get_volume_data(user_id, exercise_id, days)

        if not volume_data:
            return {'trend': 'no_data', 'data_points': []}

        # Analyze trend
        volume_analysis = self.readiness_analyzer.analyze_volume_readiness(volume_data)

        return {
            'trend': volume_analysis.get('trend', 'unknown'),
            'data_points': [{
                'date': d['date'],
                'avg_weight': d['avg_intensity'],
                'total_volume': d['total_volume'],
                'total_sets': d['total_sets']
            } for d in volume_data],
            'days_analyzed': days,
            'volume_change': volume_analysis.get('volume_change', 0)
        }

    def record_progression(self, user_id: int, exercise_id: int,
                          old_weight: float, new_weight: float,
                          progression_type: str = 'weight_increase',
                          notes: str = '') -> bool:
        """Record progression - backward compatible method"""
        self.new_service.set_user_id(user_id)
        return self.new_service.record_progression(exercise_id, old_weight, new_weight, progression_type, notes)


class AdvancedProgressionService:
    """Adapter class providing backward compatibility with old AdvancedProgressionService API"""

    def __init__(self, db_path=None):
        # Initialize with connection manager
        from models.database.connection_manager import get_db_manager
        self.connection_manager = get_db_manager()

        # Initialize components
        self.workout_repo = WorkoutRepository(None, self.connection_manager)
        self.progression_repo = ProgressionRepository(None, self.connection_manager)
        self.pattern_analyzer = PatternAnalyzer()
        self.readiness_analyzer = ReadinessAnalyzer()
        self.weight_calculator = WeightCalculator()

    def analyze_set_progression(self, user_id: int, exercise_id: int, set_number: int) -> Dict:
        """Analyze set progression"""
        # Get user preferences
        prefs = self.progression_repo.get_user_preferences(user_id) or {
            'min_reps_target': 10,
            'max_reps_target': 15,
            'weight_increment_upper': 2.5,
            'weight_increment_lower': 5.0
        }

        # Get exercise info
        exercise_info = self.workout_repo.get_exercise_info(exercise_id) or {}
        is_upper_body = self.weight_calculator.is_upper_body_exercise(exercise_info)

        # Get set history
        set_history = self.get_set_history(user_id, exercise_id, set_number)

        # Analyze readiness
        return self.readiness_analyzer.analyze_set_progression(
            set_history, prefs, exercise_info, is_upper_body
        )

    def get_set_history(self, user_id: int, exercise_id: int, set_number: int, limit: int = 5) -> List[Dict]:
        """Get set history"""
        return self.workout_repo.get_set_history(user_id, exercise_id, set_number, limit)

    def detect_pyramid_pattern(self, user_id: int, exercise_id: int) -> Dict:
        """Detect pyramid pattern"""
        workouts = self.workout_repo.get_recent_workouts(user_id, exercise_id, days=30, limit=5)
        pattern_result = self.pattern_analyzer.detect_pattern(workouts)

        # Add typical sets info
        consistency = self.pattern_analyzer.analyze_set_consistency(workouts)
        pattern_result['typical_sets'] = consistency.get('typical_sets', 3)

        return pattern_result

    def suggest_set_addition(self, user_id: int, exercise_id: int) -> Dict:
        """Suggest set addition"""
        # Get recent workouts
        workouts = self.workout_repo.get_recent_workouts(user_id, exercise_id, days=30, limit=3)

        if not workouts:
            return {'suggest_add_set': False, 'reason': 'No recent workout data'}

        # Get current typical set count
        set_counts = [len(w['sets']) for w in workouts if w.get('sets')]
        current_sets = max(set_counts) if set_counts else 0

        if current_sets == 0:
            return {'suggest_add_set': False, 'reason': 'No sets found'}

        # Check performance on current last set
        last_set_history = self.workout_repo.get_set_history(user_id, exercise_id, current_sets, limit=3)

        if len(last_set_history) < 3:
            return {'suggest_add_set': False, 'reason': 'Not enough history on current sets'}

        # Get user preferences
        prefs = self.progression_repo.get_user_preferences(user_id) or {'min_reps_target': 10}
        min_reps = prefs.get('min_reps_target', 10)

        # Check if consistently performing well on last set
        last_set_reps = [h['reps'] for h in last_set_history[:3]]
        avg_last_set_reps = sum(last_set_reps) / len(last_set_reps)

        if (avg_last_set_reps >= min_reps and
            all(c == current_sets for c in set_counts[:3]) and
            current_sets < 6):

            # Get pattern info
            pattern_info = self.detect_pyramid_pattern(user_id, exercise_id)

            # Calculate suggested weight for new set
            last_weight = last_set_history[0]['weight']
            exercise_info = self.workout_repo.get_exercise_info(exercise_id) or {}
            is_upper_body = self.weight_calculator.is_upper_body_exercise(exercise_info)

            if pattern_info['pattern'] == 'ascending':
                increment = 2.5 if is_upper_body else 5.0
                suggested_weight = last_weight + increment
            elif pattern_info['pattern'] == 'descending':
                suggested_weight = max(20, last_weight - 5.0)
            else:
                suggested_weight = last_weight

            return {
                'suggest_add_set': True,
                'reason': f'Consistently performing well on set {current_sets}',
                'current_sets': current_sets,
                'new_set_number': current_sets + 1,
                'suggested_weight': suggested_weight,
                'suggested_reps': 6,
                'pattern': pattern_info['pattern']
            }

        return {
            'suggest_add_set': False,
            'reason': f'Focus on current {current_sets} sets',
            'current_performance': f'Averaging {avg_last_set_reps:.1f} reps on last set'
        }

    def get_volume_trend(self, user_id: int, exercise_id: int, days: int = 30) -> Dict:
        """Get volume trend"""
        volume_data = self.workout_repo.get_volume_data(user_id, exercise_id, days)

        if len(volume_data) < 2:
            return {
                'trend': 'insufficient_data',
                'volume_change_percent': 0,
                'intensity_change_percent': 0
            }

        # Calculate trends
        first_volume = volume_data[0]['total_volume']
        last_volume = volume_data[-1]['total_volume']
        first_intensity = volume_data[0]['avg_intensity']
        last_intensity = volume_data[-1]['avg_intensity']

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
            'data_points': len(volume_data),
            'first_date': volume_data[0]['date'],
            'last_date': volume_data[-1]['date']
        }

    def calculate_volume_metrics(self, workout_id: int, exercise_id: int) -> Dict:
        """Calculate volume metrics"""
        return self.progression_repo.calculate_and_store_volume_metrics(workout_id, exercise_id)

    def record_set_progression(self, user_id: int, exercise_id: int, set_number: int,
                             old_weight: float, new_weight: float, old_reps: int,
                             new_reps: int, progression_type: str, notes: str = '') -> bool:
        """Record set progression"""
        return self.progression_repo.record_set_progression(
            user_id, exercise_id, set_number, old_weight, new_weight,
            old_reps, new_reps, progression_type, notes
        )

    def _get_connection(self):
        """Get database connection"""
        return self.connection_manager.get_connection()

    def _is_upper_body_exercise(self, exercise_id: int) -> bool:
        """Check if exercise is upper body"""
        exercise_info = self.workout_repo.get_exercise_info(exercise_id) or {}
        return self.weight_calculator.is_upper_body_exercise(exercise_info)
