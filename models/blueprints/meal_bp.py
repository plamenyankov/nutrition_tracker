from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from datetime import datetime, timedelta
from models.services.meal_service import MealService

meal_bp = Blueprint('meal_bp', __name__, url_prefix='/meals')
meal_service = MealService()

@meal_bp.route('')
@meal_bp.route('/<date_str>')
@login_required
def meal_tracking(date_str=None):
    """Daily meal tracking view"""
    result = meal_service.get_daily_meals(date_str)
    return render_template('nutrition_app/meal_tracking.html', **result)

@meal_bp.route('/week')
@meal_bp.route('/week/<start_date>')
@login_required
def meal_tracking_week(start_date=None):
    """Weekly meal tracking view"""
    result = meal_service.get_weekly_meals(start_date)
    return render_template('nutrition_app/meal_tracking_week.html', **result)

@meal_bp.route('/add', methods=['POST'])
@login_required
def add_to_meal():
    """Add food to a specific meal"""
    try:
        food_id = request.form.get('food_id')
        meal_type = request.form.get('meal_type', 'other')
        quantity = float(request.form.get('quantity', 1))
        date_str = request.form.get('date', datetime.now().strftime('%Y-%m-%d'))

        result = meal_service.add_food_to_meal(food_id, meal_type, quantity, date_str)

        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@meal_bp.route('/delete-consumption/<int:consumption_id>', methods=['POST'])
@login_required
def delete_consumption(consumption_id):
    """Delete a consumption item"""
    try:
        result = meal_service.delete_consumption(consumption_id)
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@meal_bp.route('/update-consumption/<int:consumption_id>', methods=['POST'])
@login_required
def update_consumption(consumption_id):
    """Update consumption quantity"""
    try:
        new_quantity = float(request.form.get('quantity', 1))
        result = meal_service.update_consumption(consumption_id, new_quantity)

        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
