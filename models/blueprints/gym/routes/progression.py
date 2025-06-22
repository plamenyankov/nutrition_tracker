"""Progression and analytics routes"""

from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from models.services.gym_service import GymService
# Use the adapter for backward compatibility
from models.services.progression_adapter import ProgressionService, AdvancedProgressionService
from datetime import datetime, timedelta
from .. import gym_bp
from ..utils.helpers import simple_set_progression_analysis, get_pyramid_description

# Initialize services
gym_service = GymService(user_id=2)


@gym_bp.route('/preferences')
@login_required
def preferences():
    """View and edit gym preferences"""
    progression_service = ProgressionService()
    user_id = gym_service.user_id
    preferences = progression_service.get_user_preferences(user_id)
    return render_template('gym/preferences.html', preferences=preferences)


@gym_bp.route('/preferences/update', methods=['POST'])
@login_required
def update_preferences():
    """Update gym preferences"""
    progression_service = ProgressionService()
    user_id = gym_service.user_id

    preferences = {
        'progression_strategy': request.form.get('progression_strategy', 'reps_first'),
        'min_reps_target': int(request.form.get('min_reps_target', 10)),
        'max_reps_target': int(request.form.get('max_reps_target', 15)),
        'weight_increment_upper': float(request.form.get('weight_increment_upper', 2.5)),
        'weight_increment_lower': float(request.form.get('weight_increment_lower', 5.0)),
        'rest_timer_enabled': request.form.get('rest_timer_enabled') == 'on',
        'progression_notification_enabled': request.form.get('progression_notification_enabled') == 'on',
        'progression_priority_1': request.form.get('progression_priority_1', 'reps'),
        'progression_priority_2': request.form.get('progression_priority_2', 'weight'),
        'progression_priority_3': request.form.get('progression_priority_3', 'volume'),
        'progression_priority_4': request.form.get('progression_priority_4', 'sets'),
        'progression_priority_5': request.form.get('progression_priority_5', 'exercises'),
        'pyramid_preference': request.form.get('pyramid_preference', 'auto_detect')
    }

    if progression_service.update_user_preferences(user_id, preferences):
        flash('Preferences updated successfully', 'success')
    else:
        flash('Error updating preferences', 'error')

    return redirect(url_for('gym.preferences'))


@gym_bp.route('/progression/suggestions')
@login_required
def progression_suggestions():
    """View progression suggestions"""
    progression_service = ProgressionService()
    user_id = gym_service.user_id

    # Get progression suggestions for the user
    exercises = gym_service.get_all_exercises()
    suggestions = []

    for exercise in exercises:
        exercise_id = exercise[0]
        readiness = progression_service.check_progression_readiness(user_id, exercise_id)
        if readiness.get('ready') or readiness.get('confidence', 0) > 0.5:
            suggestions.append({
                'exercise': exercise,
                'readiness': readiness
            })

    preferences = progression_service.get_user_preferences(user_id)

    return render_template('gym/progression/suggestions.html',
                         suggestions=suggestions,
                         preferences=preferences)


@gym_bp.route('/exercise/<int:exercise_id>/progression')
@login_required
def exercise_progression(exercise_id):
    """View exercise progression details"""
    progression_service = ProgressionService()
    user_id = gym_service.user_id

    # Get exercise info
    exercise_info = progression_service._get_exercise_info(exercise_id)
    exercise_info['id'] = exercise_id  # Add the ID to the info

    # Get progression readiness
    readiness = progression_service.check_progression_readiness(user_id, exercise_id)

    # Get performance history
    history = progression_service.get_exercise_performance_history(user_id, exercise_id, limit=10)

    # Get trend data
    trend = progression_service.get_exercise_trend(user_id, exercise_id, days=30)

    return render_template('gym/progression/exercise_detail.html',
                         exercise=exercise_info,
                         readiness=readiness,
                         history=history,
                         trend=trend)


@gym_bp.route('/exercise/<int:exercise_id>/accept-progression', methods=['POST'])
@login_required
def accept_progression(exercise_id):
    """Accept a progression suggestion"""
    progression_service = ProgressionService()
    user_id = gym_service.user_id
    data = request.json

    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400

    # Record the progression
    success = progression_service.record_progression(
        user_id,
        exercise_id,
        data.get('old_weight', 0),
        data.get('new_weight', 0),
        data.get('progression_type', 'weight_increase'),
        data.get('notes', '')
    )

    if success:
        return jsonify({'success': True, 'message': 'Progression recorded successfully'})
    else:
        return jsonify({'success': False, 'message': 'Error recording progression'}), 400


@gym_bp.route('/exercise/<int:exercise_id>/quick-progression')
@login_required
def get_exercise_quick_progression(exercise_id):
    """Get quick progression suggestion for adding exercise to workout"""
    progression_service = ProgressionService()

    # Get last performance
    last_performance = gym_service.get_last_exercise_performance(exercise_id)

    if not last_performance:
        return jsonify({
            'has_history': False,
            'suggested_weight': 0,
            'suggested_reps': 10
        })

    # Get progression readiness
    readiness = progression_service.check_progression_readiness(gym_service.user_id, exercise_id)

    # Determine suggested values
    if readiness.get('ready') and readiness.get('suggestion') == 'increase_weight':
        suggested_weight = readiness.get('new_weight', last_performance['weight'])
        suggested_reps = readiness.get('new_reps_target', 10)
    else:
        suggested_weight = last_performance['weight']
        suggested_reps = last_performance['reps']

    return jsonify({
        'has_history': True,
        'last_weight': last_performance['weight'],
        'last_reps': last_performance['reps'],
        'suggested_weight': suggested_weight,
        'suggested_reps': suggested_reps,
        'ready_for_progression': readiness.get('ready', False)
    })


@gym_bp.route('/exercise/<int:exercise_id>/progression-summary')
@login_required
def exercise_progression_summary(exercise_id):
    """Get progression summary for an exercise - used for AJAX"""
    # Get last performance for this exercise
    last_performance = gym_service.get_last_exercise_performance(exercise_id)

    if not last_performance:
        return jsonify({})

    # Calculate days since last performance
    if isinstance(last_performance.get('workout_date'), str):
        workout_date = datetime.strptime(last_performance['workout_date'], '%Y-%m-%d')
    else:
        workout_date = last_performance.get('workout_date', datetime.now())
    days_ago = (datetime.now() - workout_date).days if workout_date else 0

    # Check if ready for progression (simplified version)
    ready_for_progression = False
    if last_performance.get('reps', 0) >= 15:  # Hit upper rep range
        ready_for_progression = True

    return jsonify({
        'last_performance': {
            'weight': last_performance.get('weight', 0),
            'reps': last_performance.get('reps', 0)
        },
        'days_ago': days_ago,
        'ready_for_progression': ready_for_progression
    })


@gym_bp.route('/exercise/<int:exercise_id>/set-specific-progression/<int:set_number>')
@login_required
def get_set_specific_progression(exercise_id, set_number):
    """Get progression suggestion for specific set number"""
    adv_service = AdvancedProgressionService()
    prog_service = ProgressionService()
    user_id = gym_service.user_id

    # Get historical data for this specific set
    set_history = adv_service.get_set_history(user_id, exercise_id, set_number, limit=3)
    print(set_history)
    if not set_history:
        return jsonify({
            'has_history': False,
            'set_number': set_number,
            'suggested_weight': 0,
            'suggested_reps': 10,
            'message': f'No history for set {set_number}'
        })

    # Get the most recent performance for this set
    last_set_performance = set_history[0]

    # Analyze progression readiness for this specific set
    try:
        progression_analysis = adv_service.analyze_set_progression(user_id, exercise_id, set_number)
    except Exception as e:
        # Fallback: Simple progression analysis using current data
        progression_analysis = simple_set_progression_analysis(
            user_id, exercise_id, set_number, set_history
        )

    # Ensure progression_analysis is not None
    if not progression_analysis:
        progression_analysis = {
            'ready': False,
            'suggestion': 'maintain',
            'suggested_weight': last_set_performance['weight'],
            'suggested_reps': last_set_performance['reps'],
            'confidence': 0.0,
            'reps_to_go': 0,
            'target_reps': 15
        }

    # Determine suggested values based on progression analysis
    if progression_analysis.get('ready'):
        suggested_weight = progression_analysis.get('suggested_weight', last_set_performance['weight'])
        suggested_reps = progression_analysis.get('suggested_reps', last_set_performance['reps'])
    else:
        # Always use suggested_reps from analysis if available
        suggested_weight = progression_analysis.get('suggested_weight', last_set_performance['weight'])
        suggested_reps = progression_analysis.get('suggested_reps', last_set_performance['reps'])

        # Only fallback to last performance if no suggestion in analysis
        if suggested_reps is None:
            suggested_reps = last_set_performance['reps']

            # If close to progression, suggest slight rep increase
            if progression_analysis.get('suggestion') == 'almost_ready':
                suggested_reps = min(suggested_reps + 1, 15)  # Cap at 15 reps

    return jsonify({
        'has_history': True,
        'set_number': set_number,
        # Backend data that frontend expects
        'current_weight': last_set_performance['weight'],
        'current_avg_reps': last_set_performance['reps'],
        'last_date': last_set_performance['date'],
        'suggested_weight': suggested_weight,
        'suggested_reps': suggested_reps,
        'suggestion': progression_analysis.get('suggestion', 'maintain'),
        'ready': progression_analysis.get('ready', False),
        'confidence': progression_analysis.get('confidence', 0.0),
        'reps_to_go': progression_analysis.get('reps_to_go', 0),
        'target_reps': progression_analysis.get('target_reps', 15),
        'history_count': len(set_history),
        # Legacy fields for backward compatibility
        'last_weight': last_set_performance['weight'],
        'last_reps': last_set_performance['reps'],
        'progression_status': progression_analysis.get('suggestion', 'maintain'),
        'ready_for_progression': progression_analysis.get('ready', False)
    })


@gym_bp.route('/exercise/<int:exercise_id>/comprehensive-progression')
@login_required
def exercise_comprehensive_progression(exercise_id):
    """Get comprehensive progression data including pyramid pattern and all sets"""
    adv_service = AdvancedProgressionService()
    prog_service = ProgressionService()
    user_id = gym_service.user_id

    # Get pyramid pattern
    pyramid_data = adv_service.detect_pyramid_pattern(user_id, exercise_id)

    # Get current workout sets if in progress
    with gym_service.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT wset.id, wset.set_number, wset.weight, wset.reps
            FROM workout_sets wset
            JOIN workout_sessions ws ON wset.session_id = ws.id
            WHERE ws.user_id = %s AND wset.exercise_id = %s
                  AND ws.status = 'in_progress'
            ORDER BY wset.set_number
        ''', (user_id, exercise_id))
        current_sets = cursor.fetchall()

    # Analyze each set with detailed progression info
    sets_analysis = []
    for set_id, set_number, weight, reps in current_sets:
        progression = adv_service.analyze_set_progression(user_id, exercise_id, set_number)

        # Add historical context
        set_history = adv_service.get_set_history(user_id, exercise_id, set_number, limit=3)

        sets_analysis.append({
            'set_id': set_id,
            'set_number': set_number,
            'current_weight': weight,
            'current_reps': reps,
            'progression': progression,
            'history': set_history[:2] if set_history else []
        })

    # Get set addition suggestion
    set_addition = adv_service.suggest_set_addition(user_id, exercise_id)

    # Get user preferences for context
    preferences = prog_service.get_user_preferences(user_id)

    # Get overall exercise trend
    trend = adv_service.get_volume_trend(user_id, exercise_id, days=30)

    # Build comprehensive response
    response = {
        'pyramid': {
            'pattern': pyramid_data['pattern'],
            'confidence': pyramid_data['confidence'],
            'typical_sets': pyramid_data['typical_sets'],
            'description': get_pyramid_description(pyramid_data['pattern'])
        },
        'sets': sets_analysis,
        'set_addition': set_addition,
        'preferences': {
            'min_reps': preferences.get('min_reps_target', 10),
            'max_reps': preferences.get('max_reps_target', 15),
            'strategy': preferences.get('progression_strategy', 'reps_first')
        },
        'volume_trend': trend,
        'exercise_name': gym_service.get_exercise_by_id(exercise_id)[0] if gym_service.get_exercise_by_id(exercise_id) else 'Unknown'
    }

    return jsonify(response)


@gym_bp.route('/exercise/<int:exercise_id>/set-progression-analysis')
@login_required
def exercise_set_progression_analysis(exercise_id):
    """Get set-specific progression analysis for an exercise"""
    adv_progression_service = AdvancedProgressionService()
    user_id = gym_service.user_id

    # Get current sets for this exercise in the workout
    sets_data = []

    # Get the most recent sets for this exercise
    with gym_service.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT wset.id, wset.set_number, wset.weight, wset.reps
            FROM workout_sets wset
            JOIN workout_sessions ws ON wset.session_id = ws.id
            WHERE ws.user_id = %s AND wset.exercise_id = %s
                  AND ws.status = 'in_progress'
            ORDER BY wset.set_number
        ''', (user_id, exercise_id))
        current_sets = cursor.fetchall()

    # Analyze each set
    for set_id, set_number, weight, reps in current_sets:
        progression = adv_progression_service.analyze_set_progression(
            user_id, exercise_id, set_number
        )
        sets_data.append({
            'set_id': set_id,
            'set_number': set_number,
            'current_weight': weight,
            'current_reps': reps,
            'progression': progression
        })

    # Check if should add new set
    set_addition_suggestion = adv_progression_service.suggest_set_addition(
        user_id, exercise_id
    )

    response = {
        'sets': sets_data,
        'pyramid_pattern': adv_progression_service.detect_pyramid_pattern(user_id, exercise_id),
        **set_addition_suggestion
    }

    return jsonify(response)


@gym_bp.route('/progression/dashboard')
@login_required
def progression_dashboard():
    """Main progression dashboard with analytics - optimized version"""
    try:
        adv_progression_service = AdvancedProgressionService()
        progression_service = ProgressionService()
        user_id = gym_service.user_id

        # Initialize default values
        total_progressions = 0
        this_month = 0
        pattern_analysis = []
        recent_progressions = []
        volume_data = {'labels': [], 'volume': [], 'intensity': []}
        exercises_progress = []

        # Get metrics
        with gym_service.get_connection() as conn:
            cursor = conn.cursor()

            try:
                # Total progressions
                cursor.execute('''
                    SELECT COUNT(*) FROM progression_history WHERE user_id = %s
                ''', (user_id,))
                result = cursor.fetchone()
                total_progressions = result[0] if result else 0

                # This month progressions
                start_of_month = datetime.now().replace(day=1).strftime('%Y-%m-%d')
                cursor.execute('''
                    SELECT COUNT(*) FROM progression_history
                    WHERE user_id = %s AND progression_date >= %s
                ''', (user_id, start_of_month))
                result = cursor.fetchone()
                this_month = result[0] if result else 0

                # Get exercises with patterns - limit to reduce load
                # First get recent exercise IDs
                cursor.execute('''
                    SELECT ws.exercise_id
                    FROM workout_sets ws
                    JOIN workout_sessions wss ON ws.session_id = wss.id
                    WHERE wss.user_id = %s
                    GROUP BY ws.exercise_id
                    ORDER BY MAX(wss.date) DESC
                    LIMIT 20
                ''', (user_id,))

                recent_exercise_ids = [row[0] for row in cursor.fetchall()]

                if recent_exercise_ids:
                    # Now get exercise details
                    placeholders = ','.join(['%s'] * len(recent_exercise_ids))
                    cursor.execute(f'''
                        SELECT e.id, e.name, e.muscle_group
                        FROM exercises e
                        WHERE e.id IN ({placeholders})
                        LIMIT 12
                    ''', recent_exercise_ids)
                    exercises_with_patterns = cursor.fetchall()
                else:
                    exercises_with_patterns = []

                # Batch fetch last performances for all exercises
                exercise_ids = [ex[0] for ex in exercises_with_patterns]
                if exercise_ids:
                    placeholders = ','.join(['%s'] * len(exercise_ids))
                    cursor.execute(f'''
                        SELECT ws.exercise_id, MAX(ws.weight) as max_weight, MAX(ws.reps) as max_reps
                        FROM workout_sets ws
                        JOIN workout_sessions wss ON ws.session_id = wss.id
                        WHERE wss.user_id = %s AND ws.exercise_id IN ({placeholders})
                              AND wss.status = 'completed'
                              AND wss.date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                        GROUP BY ws.exercise_id
                    ''', [user_id] + exercise_ids)

                    last_performances = {row[0]: {'weight': row[1], 'reps': row[2]}
                                       for row in cursor.fetchall()}
                else:
                    last_performances = {}

                # Only analyze patterns for top 6 exercises
                for ex_id, name, muscle_group in exercises_with_patterns[:6]:
                    pattern_info = adv_progression_service.detect_pyramid_pattern(user_id, ex_id)

                    pattern_analysis.append({
                        'id': ex_id,
                        'name': name,
                        'muscle_group': muscle_group,
                        'pattern': pattern_info.get('pattern', 'unknown'),
                        'typical_sets': pattern_info.get('typical_sets', 3),
                        'confidence': pattern_info.get('confidence', 0)
                    })

                # Get recent progressions
                cursor.execute('''
                    SELECT ph.progression_date, e.name, ph.progression_type,
                           ph.old_weight, ph.new_weight
                    FROM progression_history ph
                    JOIN exercises e ON ph.exercise_id = e.id
                    WHERE ph.user_id = %s
                    ORDER BY ph.progression_date DESC
                    LIMIT 10
                ''', (user_id,))

                for row in cursor.fetchall():
                    event = {
                        'date': row[0],
                        'exercise': row[1],
                        'type': row[2]
                    }

                    if row[2] == 'weight' or row[2] == 'weight_increase':
                        event['old_value'] = row[3]
                        event['new_value'] = row[4]

                    recent_progressions.append(event)

                # Get volume data for chart - limit to reduce load
                thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                cursor.execute('''
                    SELECT ws.date, SUM(vt.total_volume), AVG(vt.avg_intensity)
                    FROM workout_sessions ws
                    LEFT JOIN workout_volume_tracking vt ON ws.id = vt.workout_id
                    WHERE ws.user_id = %s AND ws.date >= %s
                    GROUP BY ws.date
                    ORDER BY ws.date
                    LIMIT 30
                ''', (user_id, thirty_days_ago))

                for date, volume, intensity in cursor.fetchall():
                    volume_data['labels'].append(date)
                    volume_data['volume'].append(round(volume or 0, 1))
                    volume_data['intensity'].append(round(intensity or 0, 1))

            except Exception as e:
                # Tables might not exist or be empty
                print(f"Warning: Could not fetch progression data: {e}")
                exercises_with_patterns = []

        # Calculate volume increase
        volume_increase = 0
        if len(volume_data['volume']) >= 2:
            first_volume = volume_data['volume'][0] or 1
            last_volume = volume_data['volume'][-1] or 1
            volume_increase = round(((last_volume - first_volume) / first_volume) * 100, 1)

        # Get exercises progress - simplified version
        exercises_progressed = 0

        for ex_id, name, muscle_group in exercises_with_patterns[:12]:  # Limit to 12
            try:
                # Use cached last performance
                last_perf = last_performances.get(ex_id)

                # Simple progression check based on last performance
                ready_for_progression = False
                if last_perf and last_perf.get('reps', 0) >= 15:
                    ready_for_progression = True
                    exercises_progressed += 1

                exercises_progress.append({
                    'id': ex_id,
                    'name': name,
                    'muscle_group': muscle_group,
                    'ready_for_progression': ready_for_progression,
                    'close_to_progression': last_perf and last_perf.get('reps', 0) >= 13,
                    'current_weight': last_perf.get('weight', 0) if last_perf else 0,
                    'current_reps': last_perf.get('reps', 0) if last_perf else 0,
                    'volume_trend': 0,  # Skip for performance
                    'progress_percent': min(100, (last_perf.get('reps', 0) / 15) * 100) if last_perf else 0
                })
            except Exception as e:
                # Skip exercises that cause errors
                print(f"Warning: Could not process exercise {name}: {e}")
                continue

        metrics = {
            'total_progressions': total_progressions,
            'this_month': this_month,
            'volume_increase': volume_increase,
            'exercises_progressed': exercises_progressed,
            'total_exercises': len(exercises_with_patterns)
        }

        return render_template('gym/progression/dashboard.html',
                             metrics=metrics,
                             pattern_analysis=pattern_analysis[:6],  # Show top 6
                             recent_progressions=recent_progressions,
                             volume_chart_data=volume_data,
                             exercises_progress=exercises_progress)

    except Exception as e:
        # If there's any error, return a simple message
        flash(f'Progression dashboard temporarily unavailable: {str(e)}', 'warning')
        return redirect(url_for('gym.dashboard'))
