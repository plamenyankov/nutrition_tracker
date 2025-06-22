"""Core gym routes - dashboard, history, and basic workout management"""

from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from models.services.gym_service import GymService
from .. import gym_bp

# Initialize gym service with hardcoded user ID (matching old behavior)
gym_service = GymService(user_id=2)


@gym_bp.route('/')
@login_required
def dashboard():
    """Gym tracker dashboard"""
    recent_workouts = gym_service.get_user_workouts(5)
    return render_template('gym/dashboard.html', workouts=recent_workouts)


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
        exercise_name = set_data[16]  # Exercise name from join (after workout_sets columns)
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

    return render_template('gym/workouts/edit.html',
                         workout=workout,
                         exercises_data=exercises_data,
                         all_exercises=all_exercises,
                         workout_status=status,
                         completed_at=completed_at)


@gym_bp.route('/workout/<int:workout_id>/delete', methods=['POST'])
@login_required
def delete_workout(workout_id):
    """Delete a workout"""
    success = gym_service.delete_workout(workout_id)

    if success:
        flash('Workout deleted successfully', 'success')
    else:
        flash('Error deleting workout', 'error')

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
