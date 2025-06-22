"""Workout template management routes"""

from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from models.services.gym_service import GymService
from .. import gym_bp

# Initialize gym service
gym_service = GymService(user_id=2)


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
            template_id = gym_service.create_template(name, description, is_public)
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
    template = gym_service.get_template_by_id(template_id)
    exercises = gym_service.get_template_exercises(template_id) if template else []
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
    template = gym_service.get_template_by_id(template_id)
    template_exercises = gym_service.get_template_exercises(template_id) if template else []
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

    success = gym_service.update_template(template_id, name, description)
    if success:
        flash('Template updated successfully', 'success')
    else:
        flash('Error updating template', 'error')

    return redirect(url_for('gym.edit_template', template_id=template_id))


@gym_bp.route('/templates/<int:template_id>/add-exercise', methods=['POST'])
@login_required
def add_exercise_to_template(template_id):
    """Add an exercise to a template"""
    data = request.json
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400

    try:
        success = gym_service.add_exercise_to_template(
            template_id,
            data['exercise_id'],
            data.get('sets', 3),
            data.get('target_reps'),
            data.get('target_weight'),
            data.get('rest_seconds', 90),
            data.get('notes'),
            data['order_index']
        )
        if success:
            return jsonify({'success': True, 'message': 'Exercise added successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to add exercise'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@gym_bp.route('/templates/exercise/<int:template_exercise_id>/update', methods=['POST'])
@login_required
def update_template_exercise(template_exercise_id):
    """Update exercise in a template"""
    data = request.json
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400

    try:
        success = gym_service.update_template_exercise(
            template_exercise_id,
            data['sets'],
            data.get('target_reps'),
            data.get('target_weight'),
            data.get('rest_seconds', 90),
            data.get('notes')
        )
        if success:
            return jsonify({'success': True, 'message': 'Exercise updated successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to update exercise'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@gym_bp.route('/templates/exercise/<int:template_exercise_id>/remove', methods=['POST'])
@login_required
def remove_exercise_from_template(template_exercise_id):
    """Remove exercise from a template"""
    try:
        success = gym_service.remove_exercise_from_template(template_exercise_id)
        if success:
            return jsonify({'success': True, 'message': 'Exercise removed successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to remove exercise'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@gym_bp.route('/templates/<int:template_id>/delete', methods=['POST'])
@login_required
def delete_template(template_id):
    """Delete a workout template"""
    success = gym_service.delete_template(template_id)
    if success:
        flash('Template deleted successfully', 'success')
    else:
        flash('Error deleting template', 'error')
    return redirect(url_for('gym.templates'))


@gym_bp.route('/workout/start/<int:template_id>')
@login_required
def start_workout_from_template(template_id):
    """Start a workout from a template"""
    session_id = gym_service.start_workout_from_template(template_id)
    if session_id:
        flash('Workout started from template', 'success')
        return redirect(url_for('gym.edit_workout', workout_id=session_id))
    else:
        flash('Error starting workout from template', 'error')
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

        template_id = gym_service.create_template_from_workout(
            workout_id, name, description
        )

        if template_id:
            flash('Template created successfully!', 'success')
            return redirect(url_for('gym.template_detail', template_id=template_id))
        else:
            flash('Error creating template', 'error')
            return redirect(url_for('gym.workout_detail', workout_id=workout_id))

    # GET request - show form
    workout, sets = gym_service.get_workout_details(workout_id)
    if not workout:
        flash('Workout not found', 'error')
        return redirect(url_for('gym.history'))

    # Get exercise summary for preview
    exercises = {}
    for set_data in sets:
        exercise_name = set_data[16]  # Exercise name from join (after workout_sets columns)
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
