"""Workout logging and management routes"""

from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from models.services.gym_service import GymService
from .. import gym_bp

# Initialize gym service
gym_service = GymService(user_id=2)


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
    session_id = data.get('session_id') if data else None
    create_session_only = data.get('create_session_only', False) if data else False

    if not session_id:
        # Create new session
        try:
            session_id = gym_service.start_workout_session()
            if not session_id:
                return jsonify({'success': False, 'error': 'Failed to create workout session'}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': f'Error creating session: {str(e)}'}), 400

    # If only creating session, return early
    if create_session_only:
        return jsonify({'success': True, 'session_id': session_id})

    # Log the set
    try:
        gym_service.log_set(
            session_id,
            data['exercise_id'],
            data['set_number'],
            data['weight'],
            data['reps'],
            duration_seconds=data.get('duration_seconds', 0)
        )
        return jsonify({'success': True, 'session_id': session_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@gym_bp.route('/workout/update-set', methods=['POST'])
@login_required
def update_set():
    """Update a workout set"""
    data = request.json
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400

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
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400

    try:
        if gym_service.delete_set(data['set_id']):
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Set not found or unauthorized'}), 403
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@gym_bp.route('/workout/choose')
@login_required
def choose_workout():
    """Choose to start from template or custom workout"""
    user_templates = gym_service.get_user_templates()
    public_templates = gym_service.get_public_templates()
    return render_template('gym/workouts/choose.html',
                         user_templates=user_templates,
                         public_templates=public_templates)
