from models.food import FoodDatabase
from datetime import datetime

class RecipeService:
    def __init__(self):
        self.food_db = FoodDatabase()

    def get_all_recipes(self):
        """Get all recipes"""
        return self.food_db.fetch_all_recipes()

    def get_recipe_detail(self, recipe_id):
        """Get detailed recipe information"""
        all_recipes = self.food_db.fetch_all_recipes()
        recipe = next((r for r in all_recipes if r['recipe_id'] == recipe_id), None)

        if not recipe:
            return None

        # Get recipe ingredients
        ingredient_ids = self.food_db.fetch_recipe_ingredients(recipe_id)
        ingredients = []

        for iq_id in ingredient_ids:
            ingredient = self.food_db.fetch_nutrition(iq_id)
            ingredients.append(ingredient)

        # Calculate per serving nutrition
        per_serving = {
            'kcal': round(recipe['kcal'] / recipe['serv'], 1),
            'protein': round(recipe['protein'] / recipe['serv'], 1),
            'carb': round(recipe['carb'] / recipe['serv'], 1),
            'fat': round(recipe['fat'] / recipe['serv'], 1)
        }

        return {
            'recipe': recipe,
            'ingredients': ingredients,
            'per_serving': per_serving
        }

    def get_recipe_for_edit(self, recipe_id):
        """Get recipe data for editing"""
        all_recipes = self.food_db.fetch_all_recipes()
        recipe = next((r for r in all_recipes if r['recipe_id'] == recipe_id), None)

        if not recipe:
            return None

        # Get recipe ingredients
        ingredient_ids = self.food_db.fetch_recipe_ingredients(recipe_id)
        ingredients = []
        for iq_id in ingredient_ids:
            ingredient = self.food_db.fetch_nutrition(iq_id)
            ingredients.append(ingredient)

        # Get all foods for ingredient selection
        all_foods = self.food_db.fetch_all_nutrition()

        return {
            'recipe': recipe,
            'ingredients': ingredients,
            'foods': all_foods
        }

    def create_recipe(self, form_data):
        """Create a new recipe"""
        try:
            recipe_name = form_data.get('recipe_name')
            servings = int(form_data.get('servings', 1))

            # Get ingredients data
            ingredient_ids = form_data.getlist('ingredient_ids[]')
            quantities = form_data.getlist('quantities[]')

            if not recipe_name or not ingredient_ids:
                return {
                    'success': False,
                    'message': 'Recipe name and at least one ingredient are required'
                }

            # Build CSV data for the recipe
            csv_lines = ['ingr,qty,unit,kcal,fats,carbs,fiber,net_carbs,protein']

            for i, iq_id in enumerate(ingredient_ids):
                if iq_id:
                    # Get ingredient details
                    ingredient = self.food_db.fetch_nutrition(iq_id)
                    quantity = float(quantities[i]) if i < len(quantities) else ingredient['qty']

                    # Scale nutrition values
                    scale = quantity / ingredient['qty']

                    csv_line = f"{ingredient['ingredient']},{quantity},{ingredient['unit']}," \
                             f"{ingredient['kcal'] * scale},{ingredient['fat'] * scale}," \
                             f"{ingredient['carb'] * scale},{ingredient['fiber'] * scale}," \
                             f"{ingredient['net_carb'] * scale},{ingredient['protein'] * scale}"
                    csv_lines.append(csv_line)

            # Save recipe
            csv_data = '\n'.join(csv_lines)
            date = datetime.now().strftime('%Y-%m-%d')
            result = self.food_db.save_recipe(date, recipe_name, servings, csv_data)

            if isinstance(result, list):
                return {
                    'success': True,
                    'message': f'Recipe "{recipe_name}" created successfully!'
                }
            else:
                return {
                    'success': False,
                    'message': f'Error creating recipe: {result}'
                }

        except Exception as e:
            return {
                'success': False,
                'message': f'Error creating recipe: {str(e)}'
            }

    def delete_recipe(self, recipe_id):
        """Delete a recipe"""
        all_recipes = self.food_db.fetch_all_recipes()
        recipe = next((r for r in all_recipes if r['recipe_id'] == recipe_id), None)

        if not recipe:
            return {'success': False, 'error': 'Recipe not found'}

        result = self.food_db.delete_recipe(recipe_id)

        if "successfully" in result:
            return {
                'success': True,
                'message': f'Recipe "{recipe["recipe_name"]}" has been deleted successfully!'
            }
        else:
            return {'success': False, 'error': result}

    def add_recipe_to_meal(self, recipe_id, meal_type, servings, date_str):
        """Add recipe to a meal"""
        # Convert date format
        date = self._convert_date_format(date_str)

        # Get recipe ingredients
        ingredient_ids = self.food_db.fetch_recipe_ingredients(recipe_id)

        # Add each ingredient to the meal with scaled quantity
        for iq_id in ingredient_ids:
            ingredient = self.food_db.fetch_nutrition(iq_id)
            # Scale by number of servings consumed
            scaled_qty = ingredient['qty'] * servings

            # Get ingredient and unit IDs
            ingredient_id, unit_id = self.food_db.get_unit_ingredient_from_iq(iq_id)

            # Save with scaled quantity
            new_iq_id = self.food_db.save_ingredient_qty(scaled_qty, ingredient_id, unit_id)
            self.food_db.save_consumption(date, new_iq_id, meal_type)

        return {
            'success': True,
            'message': f'Recipe added to {meal_type}!'
        }

    def get_all_foods(self):
        """Get all foods for recipe creation"""
        return self.food_db.fetch_all_nutrition()

    def _convert_date_format(self, date_str):
        """Convert date from various formats to DD.MM.YYYY"""
        if not date_str:
            return datetime.now().strftime('%d.%m.%Y')

        # Convert DD.MM.YYYY format
        if '.' in date_str:
            return date_str

        # Convert YYYY-MM-DD format
        if '-' in date_str and len(date_str.split('-')[0]) == 4:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            return date_obj.strftime('%d.%m.%Y')

        # Default
        return datetime.now().strftime('%d.%m.%Y')
