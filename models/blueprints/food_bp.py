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
    """
    Get paginated food list with search and filters
    ---
    tags:
      - Food Database
    security:
      - LoginRequired: []
    parameters:
      - name: page
        in: query
        type: integer
        default: 1
        description: Page number
      - name: per_page
        in: query
        type: integer
        default: 24
        description: Items per page
      - name: search
        in: query
        type: string
        description: Search term for food names
      - name: favorites_only
        in: query
        type: boolean
        description: Show only favorite foods
      - name: min_calories
        in: query
        type: number
        description: Minimum calories filter
      - name: max_calories
        in: query
        type: number
        description: Maximum calories filter
    responses:
      200:
        description: Paginated food list
        schema:
          type: object
          properties:
            success:
              type: boolean
            foods:
              type: array
              items:
                type: object
                properties:
                  ingredient_id:
                    type: integer
                  name:
                    type: string
                  kcal:
                    type: number
                  protein:
                    type: number
                  carb:
                    type: number
                  fat:
                    type: number
                  is_favorite:
                    type: boolean
            pagination:
              type: object
              properties:
                page:
                  type: integer
                per_page:
                  type: integer
                total:
                  type: integer
                pages:
                  type: integer
    """
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
    """
    Add a new food to the database
    ---
    tags:
      - Food Database
    security:
      - LoginRequired: []
    parameters:
      - name: food_name
        in: formData
        type: string
        required: true
        description: Name of the food
      - name: quantity
        in: formData
        type: number
        required: true
        description: Quantity/serving size
      - name: unit
        in: formData
        type: string
        required: true
        description: Unit of measurement (g, ml, piece, etc.)
      - name: calories
        in: formData
        type: number
        required: true
        description: Calories per serving
      - name: protein
        in: formData
        type: number
        required: true
        description: Protein in grams
      - name: carbs
        in: formData
        type: number
        required: true
        description: Carbohydrates in grams
      - name: fat
        in: formData
        type: number
        required: true
        description: Fat in grams
      - name: fiber
        in: formData
        type: number
        description: Fiber in grams (optional)
    responses:
      200:
        description: Food added successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
            message:
              type: string
            food_id:
              type: integer
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
