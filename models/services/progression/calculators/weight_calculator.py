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
        """Calculate smart weight increment based on exercise type and current weight"""
        exercise_name = exercise_info.get('name', '').lower()
        equipment_type = WeightCalculator.get_equipment_type(exercise_info)

        # Base increments from user preferences or defaults
        if user_prefs:
            base_increment = user_prefs.get('weight_increment_upper' if is_upper_body else 'weight_increment_lower',
                                          2.5 if is_upper_body else 5.0)
        else:
            base_increment = 2.5 if is_upper_body else 5.0

        if equipment_type == 'bodyweight':
            # For bodyweight exercises, suggest adding weight or progressing to harder variation
            return 2.5 if current_weight == 0 else 2.5

        elif equipment_type == 'machine':
            # Machine exercises typically use 5kg increments due to plate limitations
            if current_weight < 20:
                return 2.5  # Smaller increment for lighter weights
            else:
                return 5.0  # Standard machine increment

        elif equipment_type == 'free_weight':
            # Free weights allow more precise increments
            if current_weight < 10:
                return 0.5  # Very small increment for light weights
            elif current_weight < 30:
                return 1.0  # Small increment for moderate weights
            elif current_weight < 60:
                return 2.5  # Standard increment
            else:
                return 5.0 if not is_upper_body else 2.5  # Larger increment for heavy weights

        else:
            # Default to user preferences with smart adjustments
            if current_weight < 20:
                return base_increment / 2  # Smaller increment for lighter weights
            elif current_weight > 100:
                return base_increment * 2  # Larger increment for very heavy weights
            else:
                return base_increment

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
