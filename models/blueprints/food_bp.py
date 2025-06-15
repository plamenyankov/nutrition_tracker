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
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('nutrition_app/food_database.html', today=today)

@food_bp.route('/api/paginated')
@login_required
def get_foods_paginated():
    """Get paginated foods with search and filters"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 24))
        search = request.args.get('search', '').strip()

        # Filters
        filters = {}
        if request.args.get('favorites_only') == 'true':
            filters['favorites_only'] = True
        if request.args.get('min_calories'):
            filters['min_calories'] = float(request.args.get('min_calories'))
        if request.args.get('max_calories'):
            filters['max_calories'] = float(request.args.get('max_calories'))
        if request.args.get('min_protein'):
            filters['min_protein'] = float(request.args.get('min_protein'))
        if request.args.get('max_protein'):
            filters['max_protein'] = float(request.args.get('max_protein'))

        result = food_service.get_foods_paginated(page, per_page, search, filters)
        return jsonify(result)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

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

@food_bp.route('/add', methods=['POST'])
@login_required
def add_food():
    """Add a new food to the database"""
    try:
        food_data = {
            'food_name': request.form.get('food_name'),
            'quantity': request.form.get('quantity'),
            'unit': request.form.get('unit'),
            'calories': request.form.get('calories'),
            'protein': request.form.get('protein'),
            'carbs': request.form.get('carbs'),
            'fat': request.form.get('fat'),
            'fiber': request.form.get('fiber', 0)
        }

        result = food_service.add_food(food_data)
        return jsonify(result)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@food_bp.route('/get/<int:food_id>', methods=['GET'])
@login_required
def get_food(food_id):
    """Get details of a specific food"""
    try:
        result = food_service.get_food_details(food_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@food_bp.route('/update/<int:food_id>', methods=['POST'])
@login_required
def update_food(food_id):
    """Update an existing food"""
    try:
        food_data = {
            'quantity': request.form.get('quantity'),
            'calories': request.form.get('calories'),
            'protein': request.form.get('protein'),
            'carbs': request.form.get('carbs'),
            'fat': request.form.get('fat'),
            'fiber': request.form.get('fiber', 0)
        }

        result = food_service.update_food(food_id, food_data)
        return jsonify(result)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@food_bp.route('/delete/<int:food_id>', methods=['POST'])
@login_required
def delete_food(food_id):
    """Delete a food from the database"""
    try:
        result = food_service.delete_food(food_id)
        return jsonify(result)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
