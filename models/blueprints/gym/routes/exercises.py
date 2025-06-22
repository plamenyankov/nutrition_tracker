"""Exercise management routes"""

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from models.services.gym_service import GymService
from .. import gym_bp

# Initialize gym service
gym_service = GymService(user_id=2)


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


@gym_bp.route('/exercises/edit/<int:exercise_id>', methods=['GET', 'POST'])
@login_required
def edit_exercise(exercise_id):
    """Edit an exercise"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        muscle_group = request.form.get('muscle_group', '').strip()

        if not name:
            flash('Exercise name is required', 'error')
            return redirect(url_for('gym.edit_exercise', exercise_id=exercise_id))

        success, message = gym_service.update_exercise(exercise_id, name, muscle_group)
        if success:
            flash('Exercise updated successfully', 'success')
            return redirect(url_for('gym.exercises'))
        else:
            flash(message, 'error')
            return redirect(url_for('gym.edit_exercise', exercise_id=exercise_id))

    # GET request
    exercise = gym_service.get_exercise_by_id(exercise_id)
    if not exercise:
        flash('Exercise not found', 'error')
        return redirect(url_for('gym.exercises'))

    return render_template('gym/exercises/edit.html', exercise=exercise)


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
