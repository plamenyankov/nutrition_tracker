from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models.food import FoodDatabase
from models import openai_utils
import pandas as pd
import io
from datetime import datetime, timedelta

# Create blueprint for the reorganized app
nutrition_app = Blueprint('nutrition_app', __name__)
food_db = FoodDatabase()

# Temporary storage for OpenAI results (will be improved later)
temp_ai_results = None

@nutrition_app.route('/foods')
@login_required
def food_database():
    """Food Database - View and manage all foods"""
    # Get all foods from database
    foods = food_db.fetch_all_nutrition()

    # Get today's date for the date picker
    today = datetime.now().strftime('%Y-%m-%d')

    return render_template('nutrition_app/food_database.html', foods=foods, today=today)

@nutrition_app.route('/ai-assistant', methods=['GET', 'POST'])
@login_required
def ai_assistant():
    """AI Assistant - OpenAI nutrition analysis"""
    global temp_ai_results

    if request.method == 'POST':
        user_input = request.form.get('foods', '')
        if user_input:
            try:
                # Get OpenAI response
                response = openai_utils.get_openai_response(user_input)
                # Parse CSV response
                data_io = io.StringIO(response)
                temp_ai_results = pd.read_csv(data_io)
                flash('Analysis complete! Review the results below.', 'success')
            except Exception as e:
                flash(f'Error analyzing foods: {str(e)}', 'danger')
                temp_ai_results = None

    # Convert results to dict for template
    results = None
    columns = None
    if temp_ai_results is not None:
        results = temp_ai_results.to_dict(orient='records')
        columns = temp_ai_results.columns.tolist()

    return render_template('nutrition_app/ai_assistant.html', results=results, columns=columns)

@nutrition_app.route('/meals')
@nutrition_app.route('/meals/<date_str>')
@login_required
def meal_tracking(date_str=None):
    """Meal Tracking - Track daily consumption"""
    # Parse the date parameter or use today
    if date_str:
        try:
            # Convert from YYYY-MM-DD to datetime
            selected_date = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            # Invalid date format, use today
            selected_date = datetime.now()
    else:
        selected_date = datetime.now()

    # Get all consumption data
    all_consumption = food_db.fetch_all_consumption()
    consumption_df = pd.DataFrame(all_consumption)

    # Initialize meal types
    meal_types = ['breakfast', 'lunch', 'dinner', 'snacks', 'other']
    meals_by_type = {meal: [] for meal in meal_types}

    # Initialize daily totals and meal totals
    daily_totals = {
        'calories': 0,
        'protein': 0,
        'carbs': 0,
        'fat': 0
    }

    meal_totals = {meal: {
        'calories': 0,
        'protein': 0,
        'carbs': 0,
        'fat': 0
    } for meal in meal_types}

    if not consumption_df.empty:
        # Handle multiple date formats
        def parse_date(date_str):
            """Try multiple date formats"""
            formats = ['%d.%m.%Y', '%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y']
            for fmt in formats:
                try:
                    return pd.to_datetime(date_str, format=fmt)
                except:
                    continue
            # If all formats fail, try pandas' default parser
            return pd.to_datetime(date_str)

        consumption_df['date'] = consumption_df['date'].apply(parse_date)

        # Filter for selected date
        selected_date_normalized = pd.Timestamp(selected_date).normalize()
        day_consumption = consumption_df[consumption_df['date'] == selected_date_normalized]

        if not day_consumption.empty:
            # Group by meal type
            for meal_type in meal_types:
                meal_data = day_consumption[day_consumption['meal_type'] == meal_type]
                if not meal_data.empty:
                    meals_by_type[meal_type] = meal_data.to_dict(orient='records')
                    # Calculate totals for this meal type
                    meal_totals[meal_type]['calories'] = round(meal_data['kcal'].sum(), 1)
                    meal_totals[meal_type]['protein'] = round(meal_data['protein'].sum(), 1)
                    meal_totals[meal_type]['carbs'] = round(meal_data['carb'].sum(), 1)
                    meal_totals[meal_type]['fat'] = round(meal_data['fat'].sum(), 1)

            # Calculate daily totals
            daily_totals['calories'] = round(day_consumption['kcal'].sum(), 1)
            daily_totals['protein'] = round(day_consumption['protein'].sum(), 1)
            daily_totals['carbs'] = round(day_consumption['carb'].sum(), 1)
            daily_totals['fat'] = round(day_consumption['fat'].sum(), 1)

        # Format dates back to string for display
        for meal_type, meals in meals_by_type.items():
            for meal in meals:
                if isinstance(meal.get('date'), pd.Timestamp):
                    meal['date'] = meal['date'].strftime('%d.%m.%Y')

    # Format selected date for display
    selected_date_str = selected_date.strftime('%Y-%m-%d')
    display_date = selected_date.strftime('%A, %B %d, %Y')

    # Calculate previous and next dates
    prev_date = (selected_date - timedelta(days=1)).strftime('%Y-%m-%d')
    next_date = (selected_date + timedelta(days=1)).strftime('%Y-%m-%d')

    return render_template('nutrition_app/meal_tracking.html',
                         meals_by_type=meals_by_type,
                         meal_totals=meal_totals,
                         daily_totals=daily_totals,
                         selected_date=selected_date_str,
                         display_date=display_date,
                         prev_date=prev_date,
                         next_date=next_date)

@nutrition_app.route('/meals/week')
@nutrition_app.route('/meals/week/<start_date>')
@login_required
def meal_tracking_week(start_date=None):
    """Meal Tracking Weekly View - See meals for a whole week"""
    # Parse the start date or use beginning of current week
    if start_date:
        try:
            week_start = datetime.strptime(start_date, '%Y-%m-%d')
        except ValueError:
            week_start = datetime.now()
    else:
        week_start = datetime.now()

    # Adjust to start of week (Monday)
    days_since_monday = week_start.weekday()
    week_start = week_start - timedelta(days=days_since_monday)

    # Get all consumption data
    all_consumption = food_db.fetch_all_consumption()
    consumption_df = pd.DataFrame(all_consumption)

    # Initialize week data
    week_data = {}
    week_totals = {}

    # Process each day of the week
    for day_offset in range(7):
        current_date = week_start + timedelta(days=day_offset)
        date_key = current_date.strftime('%Y-%m-%d')

        week_data[date_key] = {
            'date': current_date,
            'display_date': current_date.strftime('%A, %b %d'),
            'meals': {'breakfast': [], 'lunch': [], 'dinner': [], 'snacks': [], 'other': []},
            'totals': {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0}
        }

        if not consumption_df.empty:
            # Handle multiple date formats
            def parse_date(date_str):
                formats = ['%d.%m.%Y', '%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y']
                for fmt in formats:
                    try:
                        return pd.to_datetime(date_str, format=fmt)
                    except:
                        continue
                return pd.to_datetime(date_str)

            if 'date' not in consumption_df.columns:
                continue

            consumption_df['date'] = consumption_df['date'].apply(parse_date)

            # Filter for current date
            current_date_normalized = pd.Timestamp(current_date).normalize()
            day_consumption = consumption_df[consumption_df['date'] == current_date_normalized]

            if not day_consumption.empty:
                # Group by meal type
                for meal_type in ['breakfast', 'lunch', 'dinner', 'snacks', 'other']:
                    meal_data = day_consumption[day_consumption['meal_type'] == meal_type]
                    if not meal_data.empty:
                        week_data[date_key]['meals'][meal_type] = meal_data.to_dict(orient='records')

                # Calculate daily totals
                week_data[date_key]['totals']['calories'] = round(day_consumption['kcal'].sum(), 1)
                week_data[date_key]['totals']['protein'] = round(day_consumption['protein'].sum(), 1)
                week_data[date_key]['totals']['carbs'] = round(day_consumption['carb'].sum(), 1)
                week_data[date_key]['totals']['fat'] = round(day_consumption['fat'].sum(), 1)

    # Calculate week totals
    week_totals = {
        'calories': sum(day['totals']['calories'] for day in week_data.values()),
        'protein': sum(day['totals']['protein'] for day in week_data.values()),
        'carbs': sum(day['totals']['carbs'] for day in week_data.values()),
        'fat': sum(day['totals']['fat'] for day in week_data.values())
    }

    # Navigation dates
    prev_week = (week_start - timedelta(days=7)).strftime('%Y-%m-%d')
    next_week = (week_start + timedelta(days=7)).strftime('%Y-%m-%d')

    return render_template('nutrition_app/meal_tracking_week.html',
                         week_data=week_data,
                         week_totals=week_totals,
                         week_start=week_start.strftime('%Y-%m-%d'),
                         week_display=f"{week_start.strftime('%b %d')} - {(week_start + timedelta(days=6)).strftime('%b %d, %Y')}",
                         prev_week=prev_week,
                         next_week=next_week,
                         now=datetime.now)

@nutrition_app.route('/recipes')
@login_required
def recipes_list():
    """Recipes - View all recipes"""
    all_recipes = food_db.fetch_all_recipes()
    return render_template('nutrition_app/recipes.html', recipes=all_recipes)

@nutrition_app.route('/analytics')
@login_required
def analytics():
    """Analytics - View nutrition trends and insights"""
    return render_template('nutrition_app/analytics.html')

# Helper routes for AJAX/form submissions
@nutrition_app.route('/add-to-meal', methods=['POST'])
@login_required
def add_to_meal():
    """Add food to a specific meal"""
    try:
        food_id = request.form.get('food_id')
        meal_type = request.form.get('meal_type', 'other')
        quantity = float(request.form.get('quantity', 1))
        date_str = request.form.get('date', datetime.now().strftime('%Y-%m-%d'))

        # Convert date from ISO format (YYYY-MM-DD) to DD.MM.YYYY format
        if '-' in date_str and len(date_str.split('-')[0]) == 4:
            # It's in ISO format, convert it
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            date = date_obj.strftime('%d.%m.%Y')
        else:
            # Already in DD.MM.YYYY format or use today
            date = date_str if date_str else datetime.now().strftime('%d.%m.%Y')

        # Get the food details
        food = food_db.fetch_nutrition(food_id)

        # Calculate scaled nutrition if quantity is different
        if quantity != food['qty']:
            scale_factor = quantity / food['qty']
            # Create new ingredient quantity with scaled values
            ingredient_id, unit_id = food_db.get_unit_ingredient_from_iq(food_id)
            ingredient_quantity_id = food_db.save_ingredient_qty(quantity, ingredient_id, unit_id)
        else:
            ingredient_quantity_id = food_id

        # Save to consumption with meal type
        food_db.save_consumption(date, ingredient_quantity_id, meal_type)

        flash(f'Added {food["ingredient"]} to {meal_type}!', 'success')
        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@nutrition_app.route('/save-ai-results', methods=['POST'])
@login_required
def save_ai_results():
    """Save AI analysis results to food database"""
    global temp_ai_results

    if temp_ai_results is not None:
        try:
            # Save to database
            temp_ai_results.columns = temp_ai_results.columns.str.strip()
            food_db.save_to_database(temp_ai_results.to_csv(index=False))
            temp_ai_results = None
            flash('Foods saved to database successfully!', 'success')
        except Exception as e:
            flash(f'Error saving foods: {str(e)}', 'danger')

    return redirect(url_for('nutrition_app.ai_assistant'))

@nutrition_app.route('/delete-consumption/<int:consumption_id>', methods=['POST'])
@login_required
def delete_consumption(consumption_id):
    """Delete a consumption item"""
    try:
        result = food_db.delete_consumption(consumption_id)
        if "successful" in result:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@nutrition_app.route('/update-consumption/<int:consumption_id>', methods=['POST'])
@login_required
def update_consumption(consumption_id):
    """Update consumption quantity"""
    try:
        new_quantity = float(request.form.get('quantity', 1))

        # For now, we'll delete and re-add with new quantity
        # First get the consumption details
        all_consumption = food_db.fetch_all_consumption()
        consumption_item = next((c for c in all_consumption if c['consumption_id'] == consumption_id), None)

        if not consumption_item:
            return jsonify({'success': False, 'error': 'Consumption item not found'})

        # Delete old consumption
        food_db.delete_consumption(consumption_id)

        # Add new consumption with updated quantity
        ingredient_id, unit_id = food_db.get_unit_ingredient_from_iq(consumption_item['iq_id'])
        new_iq_id = food_db.save_ingredient_qty(new_quantity, ingredient_id, unit_id)
        food_db.save_consumption(consumption_item['date'], new_iq_id, consumption_item.get('meal_type', 'other'))

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
