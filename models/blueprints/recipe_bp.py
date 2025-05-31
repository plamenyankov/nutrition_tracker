from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required
from models.services.recipe_service import RecipeService

recipe_bp = Blueprint('recipe_bp', __name__, url_prefix='/recipes')
recipe_service = RecipeService()

@recipe_bp.route('')
@login_required
def recipes_list():
    """View all recipes"""
    recipes = recipe_service.get_all_recipes()
    return render_template('nutrition_app/recipes.html', recipes=recipes)

@recipe_bp.route('/<int:recipe_id>')
@login_required
def recipe_detail(recipe_id):
    """View recipe details"""
    result = recipe_service.get_recipe_detail(recipe_id)

    if result is None:
        flash('Recipe not found', 'danger')
        return redirect(url_for('recipe_bp.recipes_list'))

    return render_template('nutrition_app/recipe_detail.html', **result)

@recipe_bp.route('/create', methods=['GET', 'POST'])
@login_required
def recipe_create():
    """Create new recipe"""
    if request.method == 'POST':
        result = recipe_service.create_recipe(request.form)

        if result['success']:
            flash(result['message'], 'success')
            return redirect(url_for('recipe_bp.recipes_list'))
        else:
            flash(result['message'], 'danger')

    foods = recipe_service.get_all_foods()
    return render_template('nutrition_app/recipe_create.html', foods=foods)

@recipe_bp.route('/<int:recipe_id>/edit', methods=['GET', 'POST'])
@login_required
def recipe_edit(recipe_id):
    """Edit existing recipe"""
    if request.method == 'POST':
        flash('Recipe editing will be implemented soon!', 'info')
        return redirect(url_for('recipe_bp.recipe_detail', recipe_id=recipe_id))

    result = recipe_service.get_recipe_for_edit(recipe_id)

    if result is None:
        flash('Recipe not found', 'danger')
        return redirect(url_for('recipe_bp.recipes_list'))

    return render_template('nutrition_app/recipe_edit.html', **result)

@recipe_bp.route('/<int:recipe_id>/delete', methods=['POST'])
@login_required
def recipe_delete(recipe_id):
    """Delete a recipe"""
    try:
        result = recipe_service.delete_recipe(recipe_id)

        if result['success']:
            flash(result['message'], 'success')
            return jsonify({'success': True, 'redirect': url_for('recipe_bp.recipes_list')})
        else:
            return jsonify({'success': False, 'error': result['error']}), 400

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@recipe_bp.route('/<int:recipe_id>/add-to-meal', methods=['POST'])
@login_required
def recipe_add_to_meal(recipe_id):
    """Add recipe to a meal"""
    try:
        meal_type = request.form.get('meal_type', 'other')
        servings = float(request.form.get('servings', 1))
        date = request.form.get('date')
        as_recipe = request.form.get('as_recipe', 'true').lower() == 'true'

        result = recipe_service.add_recipe_to_meal(recipe_id, meal_type, servings, date, as_recipe)

        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
