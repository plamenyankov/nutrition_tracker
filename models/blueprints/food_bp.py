from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from datetime import datetime
from models.services.food_service import FoodService

food_bp = Blueprint('food_bp', __name__, url_prefix='/foods')
food_service = FoodService()

@food_bp.route('')
@login_required
def food_database():
    """Food Database - View and manage all foods"""
    foods = food_service.get_all_foods_with_favorites()
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('nutrition_app/food_database.html', foods=foods, today=today)

@food_bp.route('/toggle-favorite/<int:ingredient_id>', methods=['POST'])
@login_required
def toggle_favorite(ingredient_id):
    """Toggle favorite status for a food"""
    try:
        result = food_service.toggle_favorite(ingredient_id)
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
