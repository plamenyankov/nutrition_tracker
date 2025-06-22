"""
Pattern Analyzer - detects and analyzes workout patterns
"""

from typing import Dict, List, Optional
from enum import Enum
import statistics
import logging

logger = logging.getLogger(__name__)


class PatternType(Enum):
    """Workout pattern types"""
    ASCENDING = "ascending"      # Pyramid up
    DESCENDING = "descending"    # Pyramid down
    STRAIGHT = "straight"        # Same weight across sets
    PYRAMID = "pyramid"          # Up then down
    MIXED = "mixed"              # No clear pattern
    UNKNOWN = "unknown"


class PatternAnalyzer:
    """Analyzes workout patterns for exercises"""

    def __init__(self, weight_change_threshold: float = 2.5):
        self.weight_change_threshold = weight_change_threshold

    def detect_pattern(self, workouts: List[Dict]) -> Dict:
        """Detect the dominant pattern from recent workouts"""
        if not workouts:
            return {
                'pattern': PatternType.UNKNOWN.value,
                'confidence': 0.0,
                'sample_size': 0
            }

        patterns = []

        for workout in workouts:
            sets = workout.get('sets', [])
            if len(sets) >= 2:
                pattern = self._analyze_single_workout(sets)
                if pattern != PatternType.UNKNOWN:
                    patterns.append(pattern.value)

        if not patterns:
            return {
                'pattern': PatternType.UNKNOWN.value,
                'confidence': 0.0,
                'sample_size': len(workouts)
            }

        # Find most common pattern
        from collections import Counter
        pattern_counts = Counter(patterns)
        most_common_pattern, count = pattern_counts.most_common(1)[0]
        confidence = count / len(patterns)

        return {
            'pattern': most_common_pattern,
            'confidence': confidence,
            'sample_size': len(patterns),
            'pattern_distribution': dict(pattern_counts)
        }

    def _analyze_single_workout(self, sets: List[Dict]) -> PatternType:
        """Analyze pattern for a single workout"""
        if len(sets) < 2:
            return PatternType.UNKNOWN

        weights = [s['weight'] for s in sets if s.get('weight')]
        if not weights:
            return PatternType.UNKNOWN

        # Calculate weight differences
        weight_diffs = [weights[i+1] - weights[i] for i in range(len(weights)-1)]

        # Check for ascending pattern
        if all(diff >= 0 for diff in weight_diffs):
            if any(diff > self.weight_change_threshold for diff in weight_diffs):
                return PatternType.ASCENDING

        # Check for descending pattern
        if all(diff <= 0 for diff in weight_diffs):
            if any(abs(diff) > self.weight_change_threshold for diff in weight_diffs):
                return PatternType.DESCENDING

        # Check for straight sets
        if all(abs(diff) <= self.weight_change_threshold for diff in weight_diffs):
            return PatternType.STRAIGHT

        # Check for pyramid pattern (up then down)
        if len(weights) >= 3:
            max_weight = max(weights)
            max_index = weights.index(max_weight)

            if 0 < max_index < len(weights) - 1:
                # Check if weights increase to peak then decrease
                ascending_to_peak = all(weights[i+1] >= weights[i] for i in range(max_index))
                descending_from_peak = all(weights[i+1] <= weights[i] for i in range(max_index, len(weights)-1))

                if ascending_to_peak and descending_from_peak:
                    return PatternType.PYRAMID

        return PatternType.MIXED

    def analyze_set_consistency(self, workouts: List[Dict]) -> Dict:
        """Analyze consistency of set counts across workouts"""
        if not workouts:
            return {'consistent': False, 'typical_sets': 0, 'variation': 0}

        set_counts = []
        for workout in workouts:
            sets = workout.get('sets', [])
            if sets:
                set_counts.append(len(sets))

        if not set_counts:
            return {'consistent': False, 'typical_sets': 0, 'variation': 0}

        typical_sets = statistics.mode(set_counts) if len(set_counts) >= 2 else set_counts[0]
        variation = statistics.stdev(set_counts) if len(set_counts) >= 2 else 0

        # Consider consistent if variation is less than 1 set
        consistent = variation < 1.0

        return {
            'consistent': consistent,
            'typical_sets': typical_sets,
            'variation': round(variation, 2),
            'set_count_history': set_counts
        }
