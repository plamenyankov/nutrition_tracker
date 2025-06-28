"""
Weight Calculator - handles weight increment calculations and rounding
"""

from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class WeightCalculator:
    """Calculator for weight increments and practical weight rounding"""

    @staticmethod
    def is_upper_body_exercise(exercise_info: Dict) -> bool:
        """Determine if exercise is upper body based on muscle groups"""
        if not exercise_info:
            return True  # Default to upper body (smaller increments)

        lower_body_keywords = ['leg', 'glute', 'quad', 'hamstring', 'calf', 'squat', 'deadlift', 'lunge']
        name = exercise_info.get('name', '').lower()
        muscle_group = exercise_info.get('muscle_group', '').lower()

        for keyword in lower_body_keywords:
            if keyword in name or keyword in muscle_group:
                return False

        return True

    @staticmethod
    def get_equipment_type(exercise_info: Dict) -> str:
        """Determine equipment type for an exercise"""
        if not exercise_info:
            return 'unknown'

        exercise_name = exercise_info.get('name', '').lower()

        machine_keywords = ['machine', 'cable', 'lat pulldown', 'leg press', 'leg extension',
                           'leg curl', 'chest press', 'shoulder press', 'seated']
        free_weight_keywords = ['dumbbell', 'barbell', 'bench press', 'squat', 'deadlift',
                               'overhead press', 'row', 'curl']
        bodyweight_keywords = ['push up', 'pull up', 'chin up', 'dip', 'bodyweight']

        if any(keyword in exercise_name for keyword in machine_keywords):
            return 'machine'
        elif any(keyword in exercise_name for keyword in free_weight_keywords):
            return 'free_weight'
        elif any(keyword in exercise_name for keyword in bodyweight_keywords):
            return 'bodyweight'
        else:
            return 'unknown'

    @staticmethod
    def calculate_smart_increment(exercise_info: Dict, current_weight: float,
                                is_upper_body: bool, user_prefs: Optional[Dict] = None) -> float:
        """Calculate smart weight increment - always 5kg for all exercises"""
        # Always return 5kg increment regardless of exercise type or body part
        return 5.0

    @staticmethod
    def calculate_volume_based_reps(current_weight: float, current_reps: int, new_weight: float,
                                  volume_percentage: float = 0.9) -> int:
        """
        Calculate suggested reps based on volume maintenance

        Args:
            current_weight: Current weight being lifted
            current_reps: Current reps performed
            new_weight: New suggested weight
            volume_percentage: Percentage of original volume to maintain (default 90%)

        Returns:
            Suggested reps for the new weight (rounded up)
        """
        if current_weight <= 0 or new_weight <= 0:
            return max(current_reps, 10)  # Default fallback

        # Calculate current total volume
        current_volume = current_weight * current_reps

        # Calculate target volume (90% of current)
        target_volume = current_volume * volume_percentage

        # Calculate required reps for new weight to achieve target volume
        required_reps = target_volume / new_weight

        # Round up since we can't do partial reps
        import math
        suggested_reps = math.ceil(required_reps)

        # Ensure minimum of 6 reps for safety and maximum of 20 for practicality
        suggested_reps = max(6, min(20, suggested_reps))

        return suggested_reps

    @staticmethod
    def round_to_practical_weight(weight: float, exercise_info: Dict) -> float:
        """Round weight to practical increments based on equipment type"""
        equipment_type = WeightCalculator.get_equipment_type(exercise_info)

        if equipment_type == 'machine':
            # Round to nearest 2.5kg for machines
            return round(weight * 2) / 2
        elif equipment_type == 'free_weight':
            # Round to nearest 0.5kg for free weights
            return round(weight * 2) / 2
        else:
            # Default rounding to nearest 0.5kg
            return round(weight * 2) / 2

    @staticmethod
    def get_deterministic_weight(weights: list) -> float:
        """Get deterministic weight from a list of weights (most common or heaviest)"""
        if not weights:
            return 0.0

        from collections import Counter
        weight_counts = Counter(weights)

        # If there's a clear most common weight, use it
        most_common = weight_counts.most_common(1)[0]
        if most_common[1] > 1:  # Used more than once
            return most_common[0]

        # If all weights are used equally, prefer the heaviest weight
        return max(weights)
