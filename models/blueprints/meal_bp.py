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
    """
    Add food or recipe to a meal
    ---
    tags:
      - Meal Tracking
    security:
      - LoginRequired: []
    parameters:
      - name: ingredient_id
        in: formData
        type: integer
        description: Food ingredient ID (if adding food)
      - name: recipe_id
        in: formData
        type: integer
        description: Recipe ID (if adding recipe)
      - name: quantity
        in: formData
        type: number
        required: true
        description: Quantity/serving size
      - name: meal_type
        in: formData
        type: string
        required: true
        description: Type of meal (breakfast, lunch, dinner, snack)
        enum: [breakfast, lunch, dinner, snack, other]
      - name: date
        in: formData
        type: string
        required: true
        description: Date in YYYY-MM-DD format
      - name: as_recipe
        in: formData
        type: boolean
        description: Whether to add as recipe (true) or individual ingredients (false)
    responses:
      200:
        description: Item added to meal successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
            message:
              type: string
      400:
        description: Invalid input data
        schema:
          type: object
          properties:
            success:
              type: boolean
            error:
              type: string
    """
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
        is_recipe = request.form.get('is_recipe', 'false').lower() == 'true'
        result = meal_service.delete_consumption(consumption_id, is_recipe)
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
