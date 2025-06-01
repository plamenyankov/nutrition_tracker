from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from flask_login import login_required
from models.services.gym_service import GymService

gym_bp = Blueprint('gym', __name__, url_prefix='/gym')
gym_service = GymService()

@gym_bp.route('/')
@login_required
def dashboard():
    """Gym tracker dashboard"""
    recent_workouts = gym_service.get_user_workouts(5)
    return render_template('gym/dashboard.html', workouts=recent_workouts)

@gym_bp.route('/exercises')
@login_required
def exercises():
    """List all exercises"""
    exercises = gym_service.get_all_exercises()
    muscle_groups = set([ex[2] for ex in exercises if ex[2]])  # Get unique muscle groups
    return render_template('gym/exercises/list.html', exercises=exercises, muscle_groups=sorted(muscle_groups))

@gym_bp.route('/exercises/add', methods=['GET', 'POST'])
@login_required
def add_exercise():
    """Add new exercise"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        muscle_group = request.form.get('muscle_group', '').strip()

        if not name:
            flash('Exercise name is required', 'error')
            return redirect(url_for('gym.add_exercise'))

        try:
            gym_service.add_exercise(name, muscle_group if muscle_group else None)
            flash('Exercise added successfully', 'success')
            return redirect(url_for('gym.exercises'))
        except Exception as e:
            flash(f'Error adding exercise: {str(e)}', 'error')
            return redirect(url_for('gym.add_exercise'))

    return render_template('gym/exercises/add.html')

@gym_bp.route('/workout/start')
@login_required
def start_workout():
    """Start a new workout session"""
    exercises = gym_service.get_all_exercises()
    return render_template('gym/workouts/log.html', exercises=exercises)

@gym_bp.route('/workout/log', methods=['POST'])
@login_required
def log_workout():
    """Log workout sets"""
    data = request.json
    session_id = data.get('session_id')

    if not session_id:
        # Create new session
        session_id = gym_service.start_workout_session()

    # Log the set
    try:
        gym_service.log_set(
            session_id,
            data['exercise_id'],
            data['set_number'],
            data['weight'],
            data['reps']
        )
        return jsonify({'success': True, 'session_id': session_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@gym_bp.route('/workout/update-set', methods=['POST'])
@login_required
def update_set():
    """Update a workout set"""
    data = request.json
    try:
        gym_service.update_set(
            data['set_id'],
            data['weight'],
            data['reps']
        )
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@gym_bp.route('/workout/delete-set', methods=['POST'])
@login_required
def delete_set():
    """Delete a workout set"""
    data = request.json
    try:
        if gym_service.delete_set(data['set_id']):
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Set not found or unauthorized'}), 403
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@gym_bp.route('/history')
@login_required
def history():
    """View workout history"""
    workouts = gym_service.get_user_workouts(20)
    return render_template('gym/history/list.html', workouts=workouts)

@gym_bp.route('/history/<int:workout_id>')
@login_required
def workout_detail(workout_id):
    """View specific workout details"""
    workout, sets = gym_service.get_workout_details(workout_id)
    if not workout:
        flash('Workout not found', 'error')
        return redirect(url_for('gym.history'))

    # Group sets by exercise
    exercises = {}
    for set_data in sets:
        exercise_name = set_data[9]  # Exercise name from join (updated index due to new columns)
        if exercise_name not in exercises:
            exercises[exercise_name] = []
        exercises[exercise_name].append(set_data)

    return render_template('gym/history/detail.html', workout=workout, exercises=exercises)

@gym_bp.route('/history/<int:workout_id>/edit')
@login_required
def edit_workout(workout_id):
    """Edit a workout"""
    workout, _ = gym_service.get_workout_details(workout_id)
    if not workout:
        flash('Workout not found', 'error')
        return redirect(url_for('gym.history'))

    # Get workout status
    status, completed_at = gym_service.get_workout_status(workout_id)

    exercises_data = gym_service.get_workout_sets_grouped(workout_id)
    all_exercises = gym_service.get_all_exercises()

    # Check if user is on mobile device
    user_agent = request.headers.get('User-Agent', '').lower()
    is_mobile = any(device in user_agent for device in ['mobile', 'android', 'iphone', 'ipad'])

    template = 'gym/workouts/edit_mobile.html' if is_mobile else 'gym/workouts/edit.html'

    return render_template(template,
                         workout=workout,
                         exercises_data=exercises_data,
                         all_exercises=all_exercises,
                         workout_status=status,
                         completed_at=completed_at)

@gym_bp.route('/workout/update-notes', methods=['POST'])
@login_required
def update_notes():
    """Update workout notes"""
    data = request.json
    try:
        gym_service.update_workout_notes(data['workout_id'], data['notes'])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@gym_bp.route('/exercises/delete/<int:exercise_id>', methods=['POST'])
@login_required
def delete_exercise(exercise_id):
    """Delete an exercise"""
    success, message = gym_service.delete_exercise(exercise_id)
    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')
    return redirect(url_for('gym.exercises'))

@gym_bp.route('/workout/<int:workout_id>/delete', methods=['POST'])
@login_required
def delete_workout(workout_id):
    """Delete an entire workout"""
    success, message = gym_service.delete_workout(workout_id)
    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')
    return redirect(url_for('gym.history'))

@gym_bp.route('/workout/<int:workout_id>/complete', methods=['POST'])
@login_required
def complete_workout(workout_id):
    """Mark a workout as completed"""
    success, message = gym_service.complete_workout(workout_id)
    if success:
        # Get workout summary for display
        summary = gym_service.get_workout_summary(workout_id)
        flash(f'Workout completed! Duration: {summary["duration_minutes"]} minutes, Total volume: {summary["total_volume"]:.0f}kg', 'success')
    else:
        flash(message, 'error')
    return redirect(url_for('gym.workout_detail', workout_id=workout_id))

@gym_bp.route('/workout/<int:workout_id>/abandon', methods=['POST'])
@login_required
def abandon_workout(workout_id):
    """Abandon a workout"""
    success, message = gym_service.abandon_workout(workout_id)
    if success:
        flash('Workout abandoned', 'warning')
    else:
        flash(message, 'error')
    return redirect(url_for('gym.history'))

# Template Routes

@gym_bp.route('/templates')
@login_required
def templates():
    """List user's workout templates"""
    user_templates = gym_service.get_user_templates()
    public_templates = gym_service.get_public_templates()
    return render_template('gym/templates/list.html',
                         user_templates=user_templates,
                         public_templates=public_templates)

@gym_bp.route('/templates/create', methods=['GET', 'POST'])
@login_required
def create_template():
    """Create a new workout template"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        is_public = request.form.get('is_public') == 'on'

        if not name:
            flash('Template name is required', 'error')
            return redirect(url_for('gym.create_template'))

        try:
            template_id = gym_service.create_workout_template(name, description, is_public)
            flash('Template created successfully', 'success')
            return redirect(url_for('gym.edit_template', template_id=template_id))
        except Exception as e:
            flash(f'Error creating template: {str(e)}', 'error')
            return redirect(url_for('gym.create_template'))

    return render_template('gym/templates/create.html')

@gym_bp.route('/templates/<int:template_id>')
@login_required
def template_detail(template_id):
    """View template details"""
    template, exercises = gym_service.get_template_details(template_id)
    if not template:
        flash('Template not found', 'error')
        return redirect(url_for('gym.templates'))

    return render_template('gym/templates/detail.html',
                         template=template,
                         exercises=exercises,
                         current_user_id=gym_service.user_id)

@gym_bp.route('/templates/<int:template_id>/edit')
@login_required
def edit_template(template_id):
    """Edit a workout template"""
    template, template_exercises = gym_service.get_template_details(template_id)
    if not template:
        flash('Template not found', 'error')
        return redirect(url_for('gym.templates'))

    # Check if user owns this template
    if template[3] != gym_service.user_id:
        flash('You can only edit your own templates', 'error')
        return redirect(url_for('gym.templates'))

    all_exercises = gym_service.get_all_exercises()
    muscle_groups = set([ex[2] for ex in all_exercises if ex[2]])

    return render_template('gym/templates/edit.html',
                         template=template,
                         template_exercises=template_exercises,
                         all_exercises=all_exercises,
                         muscle_groups=sorted(muscle_groups))

@gym_bp.route('/templates/<int:template_id>/update', methods=['POST'])
@login_required
def update_template(template_id):
    """Update template details"""
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    is_public = request.form.get('is_public') == 'on'

    if not name:
        flash('Template name is required', 'error')
        return redirect(url_for('gym.edit_template', template_id=template_id))

    success, message = gym_service.update_template(template_id, name, description, is_public)
    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')

    return redirect(url_for('gym.edit_template', template_id=template_id))

@gym_bp.route('/templates/<int:template_id>/add-exercise', methods=['POST'])
@login_required
def add_exercise_to_template(template_id):
    """Add an exercise to a template"""
    data = request.json
    try:
        success, message = gym_service.add_exercise_to_template(
            template_id,
            data['exercise_id'],
            data['order_index'],
            data.get('sets', 3),
            data.get('target_reps'),
            data.get('target_weight'),
            data.get('rest_seconds', 90),
            data.get('notes')
        )
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@gym_bp.route('/templates/exercise/<int:template_exercise_id>/update', methods=['POST'])
@login_required
def update_template_exercise(template_exercise_id):
    """Update exercise in a template"""
    data = request.json
    try:
        success, message = gym_service.update_template_exercise(
            template_exercise_id,
            data['sets'],
            data.get('target_reps'),
            data.get('target_weight'),
            data.get('rest_seconds', 90),
            data.get('notes')
        )
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@gym_bp.route('/templates/exercise/<int:template_exercise_id>/remove', methods=['POST'])
@login_required
def remove_exercise_from_template(template_exercise_id):
    """Remove exercise from a template"""
    try:
        success, message = gym_service.remove_exercise_from_template(template_exercise_id)
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@gym_bp.route('/templates/<int:template_id>/delete', methods=['POST'])
@login_required
def delete_template(template_id):
    """Delete a workout template"""
    success, message = gym_service.delete_template(template_id)
    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')
    return redirect(url_for('gym.templates'))

@gym_bp.route('/workout/start/<int:template_id>')
@login_required
def start_workout_from_template(template_id):
    """Start a workout from a template"""
    session_id, message = gym_service.start_workout_from_template(template_id)
    if session_id:
        flash('Workout started from template', 'success')
        return redirect(url_for('gym.edit_workout', workout_id=session_id))
    else:
        flash(message, 'error')
        return redirect(url_for('gym.templates'))

@gym_bp.route('/template/from-workout/<int:workout_id>', methods=['GET', 'POST'])
@login_required
def create_template_from_workout(workout_id):
    """Create a template from an existing workout"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        is_public = request.form.get('is_public') == 'on'

        if not name:
            flash('Template name is required', 'error')
            return redirect(url_for('gym.create_template_from_workout', workout_id=workout_id))

        template_id, message = gym_service.create_template_from_workout(
            workout_id, name, description, is_public
        )

        if template_id:
            flash('Template created successfully!', 'success')
            return redirect(url_for('gym.template_detail', template_id=template_id))
        else:
            flash(message, 'error')
            return redirect(url_for('gym.workout_detail', workout_id=workout_id))

    # GET request - show form
    workout, sets = gym_service.get_workout_details(workout_id)
    if not workout:
        flash('Workout not found', 'error')
        return redirect(url_for('gym.history'))

    # Get exercise summary for preview
    exercises = {}
    for set_data in sets:
        exercise_name = set_data[9]  # Updated index due to new columns
        if exercise_name not in exercises:
            exercises[exercise_name] = {
                'sets': 0,
                'total_weight': 0,
                'total_reps': 0
            }
        exercises[exercise_name]['sets'] += 1
        exercises[exercise_name]['total_weight'] += set_data[4]
        exercises[exercise_name]['total_reps'] += set_data[5]

    # Calculate averages
    for name, data in exercises.items():
        data['avg_weight'] = round(data['total_weight'] / data['sets'], 1)
        data['avg_reps'] = round(data['total_reps'] / data['sets'])

    return render_template('gym/templates/create_from_workout.html',
                         workout=workout,
                         exercises=exercises)

# Update the existing start_workout route to show template selection
@gym_bp.route('/workout/choose')
@login_required
def choose_workout():
    """Choose to start from template or custom workout"""
    user_templates = gym_service.get_user_templates()
    public_templates = gym_service.get_public_templates()
    return render_template('gym/workouts/choose.html',
                         user_templates=user_templates,
                         public_templates=public_templates)

# Progressive Overload Routes

@gym_bp.route('/preferences')
@login_required
def preferences():
    """View and edit gym preferences"""
    from models.services.progression_service import ProgressionService
    progression_service = ProgressionService()

    user_id = gym_service.user_id
    preferences = progression_service.get_user_preferences(user_id)

    return render_template('gym/preferences.html', preferences=preferences)

@gym_bp.route('/preferences/update', methods=['POST'])
@login_required
def update_preferences():
    """Update gym preferences"""
    from models.services.progression_service import ProgressionService
    progression_service = ProgressionService()

    user_id = gym_service.user_id

    preferences = {
        'progression_strategy': request.form.get('progression_strategy', 'reps_first'),
        'min_reps_target': int(request.form.get('min_reps_target', 10)),
        'max_reps_target': int(request.form.get('max_reps_target', 15)),
        'weight_increment_upper': float(request.form.get('weight_increment_upper', 2.5)),
        'weight_increment_lower': float(request.form.get('weight_increment_lower', 5.0)),
        'rest_timer_enabled': request.form.get('rest_timer_enabled') == 'on',
        'progression_notification_enabled': request.form.get('progression_notification_enabled') == 'on'
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
    from models.services.progression_service import ProgressionService
    progression_service = ProgressionService()

    user_id = gym_service.user_id
    workout_id = request.args.get('workout_id', type=int)

    suggestions = progression_service.get_progression_suggestions(user_id, workout_id)
    preferences = progression_service.get_user_preferences(user_id)

    return render_template('gym/progression/suggestions.html',
                         suggestions=suggestions,
                         preferences=preferences)

@gym_bp.route('/exercise/<int:exercise_id>/progression')
@login_required
def exercise_progression(exercise_id):
    """View exercise progression details"""
    from models.services.progression_service import ProgressionService
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
    from models.services.progression_service import ProgressionService
    progression_service = ProgressionService()

    user_id = gym_service.user_id
    data = request.json

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
