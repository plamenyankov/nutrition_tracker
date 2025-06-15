from models.food import FoodDatabase
from datetime import datetime, timedelta
import pandas as pd

class MealService:
    def __init__(self):
        self.food_db = FoodDatabase()

    def get_daily_meals(self, date_str=None):
        """Get meals for a specific day"""
        # Parse the date parameter or use today
        if date_str:
            try:
                selected_date = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                selected_date = datetime.now()
        else:
            selected_date = datetime.now()

        # Get all consumption data
        all_consumption = self.food_db.fetch_all_consumption()
        consumption_df = pd.DataFrame(all_consumption)

        # Get recipe consumption data
        all_recipe_consumption = self.food_db.fetch_recipe_consumption()
        recipe_consumption_df = pd.DataFrame(all_recipe_consumption)

        # Initialize meal types and data structures
        meal_types = ['breakfast', 'lunch', 'dinner', 'snacks', 'other']
        meals_by_type = {meal: [] for meal in meal_types}
        daily_totals = {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0}
        meal_totals = {meal: {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0} for meal in meal_types}

        if not consumption_df.empty:
            # Handle date formats
            consumption_df['date'] = consumption_df['date'].apply(self._parse_date)

            # Filter for selected date
            selected_date_normalized = pd.Timestamp(selected_date).normalize()
            day_consumption = consumption_df[consumption_df['date'] == selected_date_normalized]

            if not day_consumption.empty:
                # Process meals by type
                for meal_type in meal_types:
                    meal_data = day_consumption[day_consumption['meal_type'] == meal_type]
                    if not meal_data.empty:
                        meals_by_type[meal_type] = meal_data.to_dict(orient='records')
                        # Calculate totals
                        meal_totals[meal_type]['calories'] = round(meal_data['kcal'].sum(), 1)
                        meal_totals[meal_type]['protein'] = round(meal_data['protein'].sum(), 1)
                        meal_totals[meal_type]['carbs'] = round(meal_data['carb'].sum(), 1)
                        meal_totals[meal_type]['fat'] = round(meal_data['fat'].sum(), 1)

                # Calculate daily totals
                daily_totals['calories'] = round(day_consumption['kcal'].sum(), 1)
                daily_totals['protein'] = round(day_consumption['protein'].sum(), 1)
                daily_totals['carbs'] = round(day_consumption['carb'].sum(), 1)
                daily_totals['fat'] = round(day_consumption['fat'].sum(), 1)

            # Format dates back to string
            for meal_type, meals in meals_by_type.items():
                for meal in meals:
                    if isinstance(meal.get('date'), pd.Timestamp):
                        meal['date'] = meal['date'].strftime('%d.%m.%Y')

        # Process recipe consumption data
        if not recipe_consumption_df.empty:
            # Handle date formats
            recipe_consumption_df['date'] = recipe_consumption_df['date'].apply(self._parse_date)

            # Filter for selected date
            day_recipes = recipe_consumption_df[recipe_consumption_df['date'] == selected_date_normalized]

            if not day_recipes.empty:
                # Add recipes to meals by type
                for meal_type in meal_types:
                    recipe_data = day_recipes[day_recipes['meal_type'] == meal_type]
                    if not recipe_data.empty:
                        # Convert recipe data to match regular food format
                        recipe_items = []
                        for _, recipe in recipe_data.iterrows():
                            recipe_item = {
                                'date': recipe['date'].strftime('%d.%m.%Y'),
                                'qty': recipe['servings'],
                                'unit': 'serving(s)',
                                'ingredient': f"[Recipe] {recipe['recipe_name']}",
                                'kcal': recipe['kcal'],
                                'fat': recipe['fat'],
                                'carb': recipe['carb'],
                                'protein': recipe['protein'],
                                'recipe_consumption_id': recipe['recipe_consumption_id'],
                                'recipe_id': recipe['recipe_id'],
                                'is_recipe': True
                            }
                            recipe_items.append(recipe_item)

                        # Add recipe items to the meal type
                        meals_by_type[meal_type].extend(recipe_items)

                        # Update totals
                        meal_totals[meal_type]['calories'] += round(recipe_data['kcal'].sum(), 1)
                        meal_totals[meal_type]['protein'] += round(recipe_data['protein'].sum(), 1)
                        meal_totals[meal_type]['carbs'] += round(recipe_data['carb'].sum(), 1)
                        meal_totals[meal_type]['fat'] += round(recipe_data['fat'].sum(), 1)

                        daily_totals['calories'] += round(recipe_data['kcal'].sum(), 1)
                        daily_totals['protein'] += round(recipe_data['protein'].sum(), 1)
                        daily_totals['carbs'] += round(recipe_data['carb'].sum(), 1)
                        daily_totals['fat'] += round(recipe_data['fat'].sum(), 1)

        # Format dates for template
        return {
            'meals_by_type': meals_by_type,
            'meal_totals': meal_totals,
            'daily_totals': daily_totals,
            'selected_date': selected_date.strftime('%Y-%m-%d'),
            'display_date': selected_date.strftime('%A, %B %d, %Y'),
            'prev_date': (selected_date - timedelta(days=1)).strftime('%Y-%m-%d'),
            'next_date': (selected_date + timedelta(days=1)).strftime('%Y-%m-%d')
        }

    def get_weekly_meals(self, start_date=None):
        """Get meals for a week"""
        # Parse start date or use beginning of current week
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
        all_consumption = self.food_db.fetch_all_consumption()
        consumption_df = pd.DataFrame(all_consumption)

        # Get recipe consumption data
        all_recipe_consumption = self.food_db.fetch_recipe_consumption()
        recipe_consumption_df = pd.DataFrame(all_recipe_consumption)

        # Initialize week data
        week_data = {}

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

            if not consumption_df.empty and 'date' in consumption_df.columns:
                consumption_df['date'] = consumption_df['date'].apply(self._parse_date)

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

            # Process recipe consumption data
            if not recipe_consumption_df.empty:
                # Handle date formats
                recipe_consumption_df['date'] = recipe_consumption_df['date'].apply(self._parse_date)

                # Filter for current date
                day_recipes = recipe_consumption_df[recipe_consumption_df['date'] == current_date_normalized]

                if not day_recipes.empty:
                    # Group by meal type
                    for meal_type in ['breakfast', 'lunch', 'dinner', 'snacks', 'other']:
                        recipe_data = day_recipes[day_recipes['meal_type'] == meal_type]
                        if not recipe_data.empty:
                            # Convert recipe data to match regular food format
                            recipe_items = []
                            for _, recipe in recipe_data.iterrows():
                                recipe_item = {
                                    'date': recipe['date'].strftime('%d.%m.%Y'),
                                    'qty': recipe['servings'],
                                    'unit': 'serving(s)',
                                    'ingredient': f"[Recipe] {recipe['recipe_name']}",
                                    'kcal': recipe['kcal'],
                                    'fat': recipe['fat'],
                                    'carb': recipe['carb'],
                                    'protein': recipe['protein'],
                                    'recipe_consumption_id': recipe['recipe_consumption_id'],
                                    'recipe_id': recipe['recipe_id'],
                                    'is_recipe': True
                                }
                                recipe_items.append(recipe_item)

                            # Add recipe items to the meal type
                            week_data[date_key]['meals'][meal_type].extend(recipe_items)

                            # Update totals
                            week_data[date_key]['totals']['calories'] += round(recipe_data['kcal'].sum(), 1)
                            week_data[date_key]['totals']['protein'] += round(recipe_data['protein'].sum(), 1)
                            week_data[date_key]['totals']['carbs'] += round(recipe_data['carb'].sum(), 1)
                            week_data[date_key]['totals']['fat'] += round(recipe_data['fat'].sum(), 1)

        # Calculate week totals
        week_totals = {
            'calories': sum(day['totals']['calories'] for day in week_data.values()),
            'protein': sum(day['totals']['protein'] for day in week_data.values()),
            'carbs': sum(day['totals']['carbs'] for day in week_data.values()),
            'fat': sum(day['totals']['fat'] for day in week_data.values())
        }

        return {
            'week_data': week_data,
            'week_totals': week_totals,
            'week_start': week_start.strftime('%Y-%m-%d'),
            'week_display': f"{week_start.strftime('%b %d')} - {(week_start + timedelta(days=6)).strftime('%b %d, %Y')}",
            'prev_week': (week_start - timedelta(days=7)).strftime('%Y-%m-%d'),
            'next_week': (week_start + timedelta(days=7)).strftime('%Y-%m-%d'),
            'now': datetime.now
        }

    def add_food_to_meal(self, food_id, meal_type, quantity, date_str):
        """Add food to a meal"""
        try:
            # Convert food_id to integer and quantity to float
            food_id = int(food_id)
            quantity = float(quantity)

            print(f"Adding food to meal: food_id={food_id}, meal_type={meal_type}, quantity={quantity}, date_str={date_str}")

            # Convert date format
            date = self._convert_date_format(date_str)
            print(f"Converted date: {date}")

            # Get food details
            food = self.food_db.fetch_nutrition(food_id)

            if not food:
                return {'success': False, 'error': 'Food not found'}

            print(f"Found food: {food['ingredient']}")

            # Handle quantity scaling
            if quantity != food['qty']:
                ingredient_id, unit_id = self.food_db.get_unit_ingredient_from_iq(food_id)
                ingredient_quantity_id = self.food_db.save_ingredient_qty(quantity, ingredient_id, unit_id)
                print(f"Created new ingredient quantity: {ingredient_quantity_id}")
            else:
                ingredient_quantity_id = food_id
                print(f"Using existing ingredient quantity: {ingredient_quantity_id}")

            # Save to consumption
            result = self.food_db.save_consumption(date, ingredient_quantity_id, meal_type)
            print(f"Save consumption result: {result}")

            return {
                'success': True,
                'message': f'Added {food["ingredient"]} to {meal_type}!'
            }
        except ValueError as e:
            print(f"ValueError in add_food_to_meal: {e}")
            return {'success': False, 'error': f'Invalid input: {str(e)}'}
        except Exception as e:
            print(f"Exception in add_food_to_meal: {e}")
            return {'success': False, 'error': str(e)}

    def delete_consumption(self, consumption_id, is_recipe=False):
        """Delete a consumption item"""
        try:
            if is_recipe:
                result = self.food_db.delete_recipe_consumption(consumption_id)
            else:
                result = self.food_db.delete_consumption(consumption_id)

            if "successful" in result:
                return {'success': True}
            else:
                return {'success': False, 'error': result}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def update_consumption(self, consumption_id, new_quantity):
        """Update consumption quantity"""
        try:
            # Get consumption details
            all_consumption = self.food_db.fetch_all_consumption()
            consumption_item = next((c for c in all_consumption if c['consumption_id'] == consumption_id), None)

            if not consumption_item:
                return {'success': False, 'error': 'Consumption item not found'}

            # Delete old consumption
            self.food_db.delete_consumption(consumption_id)

            # Add new consumption with updated quantity
            ingredient_id, unit_id = self.food_db.get_unit_ingredient_from_iq(consumption_item['iq_id'])
            new_iq_id = self.food_db.save_ingredient_qty(new_quantity, ingredient_id, unit_id)
            self.food_db.save_consumption(
                consumption_item['date'],
                new_iq_id,
                consumption_item.get('meal_type', 'other')
            )

            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _parse_date(self, date_str):
        """Parse dates in multiple formats"""
        formats = ['%d.%m.%Y', '%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y']
        for fmt in formats:
            try:
                return pd.to_datetime(date_str, format=fmt)
            except:
                continue
        return pd.to_datetime(date_str)

    def _convert_date_format(self, date_str):
        """Convert date to the format expected by the database"""
        if '-' in date_str and len(date_str.split('-')[0]) == 4:
            # Already in YYYY-MM-DD format, return as is for MySQL
            return date_str
        else:
            # Convert other formats to YYYY-MM-DD for MySQL compatibility
            if date_str:
                try:
                    # Try to parse DD.MM.YYYY format
                    if '.' in date_str:
                        date_obj = datetime.strptime(date_str, '%d.%m.%Y')
                    else:
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    return date_obj.strftime('%Y-%m-%d')
                except:
                    return datetime.now().strftime('%Y-%m-%d')
            else:
                return datetime.now().strftime('%Y-%m-%d')
