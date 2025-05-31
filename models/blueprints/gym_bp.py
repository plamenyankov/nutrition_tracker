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
        exercise_name = set_data[6]  # Exercise name from join
        if exercise_name not in exercises:
            exercises[exercise_name] = []
        exercises[exercise_name].append(set_data)

    return render_template('gym/history/detail.html', workout=workout, exercises=exercises)

@gym_bp.route('/history/<int:workout_id>/edit')
@login_required
def edit_workout(workout_id):
    """Edit a completed workout"""
    workout, _ = gym_service.get_workout_details(workout_id)
    if not workout:
        flash('Workout not found', 'error')
        return redirect(url_for('gym.history'))

    exercises_data = gym_service.get_workout_sets_grouped(workout_id)
    all_exercises = gym_service.get_all_exercises()

    return render_template('gym/workouts/edit.html',
                         workout=workout,
                         exercises_data=exercises_data,
                         all_exercises=all_exercises)

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
