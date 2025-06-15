from flask import Blueprint, request, jsonify, session
from models.services.workout_timer_service import WorkoutTimerService

timer_bp = Blueprint('timer', __name__)

@timer_bp.route('/api/timer/workout/start', methods=['POST'])
def start_workout_timer():
    """Start timing a workout session"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        notes = data.get('notes')

        if not session_id:
            return jsonify({'error': 'Session ID is required'}), 400

        timer_service = WorkoutTimerService()
        result = timer_service.start_workout_timer(session_id, notes)

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@timer_bp.route('/api/timer/workout/complete', methods=['POST'])
def complete_workout_timer():
    """Complete timing a workout session"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')

        if not session_id:
            return jsonify({'error': 'Session ID is required'}), 400

        timer_service = WorkoutTimerService()
        result = timer_service.complete_workout_timer(session_id)

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@timer_bp.route('/api/timer/set/complete', methods=['POST'])
def complete_set_timer():
    """Complete timing for a specific set"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        exercise_id = data.get('exercise_id')
        set_id = data.get('set_id')

        if not all([session_id, exercise_id, set_id]):
            return jsonify({'error': 'Session ID, exercise ID, and set ID are required'}), 400

        timer_service = WorkoutTimerService()
        result = timer_service.complete_set_timer(session_id, exercise_id, set_id)

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@timer_bp.route('/api/timer/workout/summary/<int:session_id>')
def get_workout_timing_summary(session_id):
    """Get comprehensive timing summary for a workout"""
    try:
        timer_service = WorkoutTimerService()
        result = timer_service.get_workout_timing_summary(session_id)

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
