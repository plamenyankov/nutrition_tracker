"""Helper functions for gym blueprint"""


def get_pyramid_description(pattern):
    """Get user-friendly description of pyramid pattern"""
    descriptions = {
        'ascending': 'Weight increases with each set (light → heavy)',
        'descending': 'Weight decreases with each set (heavy → light)',
        'straight': 'Same weight across all sets',
        'mixed': 'Variable weight pattern',
        'unknown': 'Pattern not yet established'
    }
    return descriptions.get(pattern, 'Custom pattern')


def simple_set_progression_analysis(user_id, exercise_id, set_number, set_history):
    """Simple fallback progression analysis when AdvancedProgressionService fails"""
    if len(set_history) < 2:
        current = set_history[0] if set_history else None
        if current:
            # For single history entry, suggest maintaining or slightly improving
            return {
                'ready': False,
                'confidence': 0.0,
                'suggestion': 'build_strength',
                'current_weight': current['weight'],
                'suggested_weight': current['weight'],
                'suggested_reps': max(current['reps'] + 1, 10),  # Suggest at least 1 more rep
                'current_avg_reps': current['reps'],
                'reps_to_go': max(1, 15 - current['reps']),
                'target_reps': 15
            }
        else:
            return {
                'ready': False,
                'confidence': 0.0,
                'suggestion': 'maintain',
                'current_weight': 0,
                'suggested_weight': 0,
                'suggested_reps': 10,
                'reps_to_go': 5,
                'target_reps': 15
            }

    current = set_history[0]
    current_weight = current['weight']
    current_reps = current['reps']

    # Find the best performance at current weight
    best_reps_at_weight = current_reps
    for entry in set_history:
        if entry['weight'] == current_weight:
            best_reps_at_weight = max(best_reps_at_weight, entry['reps'])

    # Check if recently progressed by comparing with older data
    recently_progressed = False
    for i in range(1, min(len(set_history), 4)):
        if set_history[i]['weight'] < current_weight:
            recently_progressed = True
            break

    # Simple progression logic
    if recently_progressed:
        if current_reps >= 15:  # max_reps
            # Import WeightCalculator for volume-based calculation
            from models.services.progression.calculators.weight_calculator import WeightCalculator
            new_weight = current_weight + 5.0  # Always 5kg increment
            suggested_reps = WeightCalculator.calculate_volume_based_reps(
                current_weight, current_reps, new_weight
            )
            return {
                'ready': True,
                'confidence': 0.9,
                'suggestion': 'increase_weight',
                'current_weight': current_weight,
                'suggested_weight': new_weight,
                'suggested_reps': suggested_reps,
                'reps_to_go': 0,
                'target_reps': 15
            }
        else:
            # Never suggest fewer reps than the best achieved at this weight
            target_reps = max(best_reps_at_weight + 1, 15)
            return {
                'ready': False,
                'confidence': 0.7,
                'suggestion': 'build_strength',
                'current_weight': current_weight,
                'current_avg_reps': current_reps,
                'suggested_reps': max(current_reps + 1, best_reps_at_weight),
                'reps_to_go': max(1, target_reps - current_reps),
                'target_reps': target_reps
            }
    else:
        # Standard progression logic
        if current_reps >= 15:
            # Import WeightCalculator for volume-based calculation
            from models.services.progression.calculators.weight_calculator import WeightCalculator
            new_weight = current_weight + 5.0  # Always 5kg increment
            suggested_reps = WeightCalculator.calculate_volume_based_reps(
                current_weight, current_reps, new_weight
            )
            return {
                'ready': True,
                'confidence': 0.9,
                'suggestion': 'increase_weight',
                'current_weight': current_weight,
                'suggested_weight': new_weight,
                'suggested_reps': suggested_reps,
                'reps_to_go': 0,
                'target_reps': 15
            }
        else:
            # Always aim for at least best performance + 1 rep
            target_reps = max(best_reps_at_weight + 1, 15)
            return {
                'ready': False,
                'confidence': 0.5,
                'suggestion': 'increase_reps',
                'current_weight': current_weight,
                'current_avg_reps': current_reps,
                'suggested_reps': max(current_reps + 1, best_reps_at_weight),
                'reps_to_go': max(1, target_reps - current_reps),
                'target_reps': target_reps
            }
