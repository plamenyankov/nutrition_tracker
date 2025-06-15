from models.food import FoodDatabase
from datetime import datetime

class RecipeService:
    def __init__(self):
        self.food_db = FoodDatabase()

    def __del__(self):
        """Cleanup when service is destroyed"""
        try:
            if hasattr(self, 'food_db') and self.food_db:
                self.food_db.close()
        except:
            pass  # Ignore cleanup errors

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

        # Get usage count
        usage_count = self.get_recipe_usage_count(recipe_id)

        return {
            'recipe': recipe,
            'ingredients': ingredients,
            'foods': all_foods,
            'usage_count': usage_count
        }

    def get_recipe_usage_count(self, recipe_id):
        """Get how many times a recipe has been used in meal tracking"""
        try:
            # Get recipe consumption records for this specific recipe only
            # This is more efficient than fetching all consumption records
            with self.food_db.connection_manager.get_connection() as conn:
                cursor = conn.cursor()
                if self.food_db.connection_manager.use_mysql:
                    cursor.execute('SELECT COUNT(*) FROM recipe_consumption WHERE recipe_id = %s', (recipe_id,))
                else:
                    cursor.execute('SELECT COUNT(*) FROM recipe_consumption WHERE recipe_id = ?', (recipe_id,))

                result = cursor.fetchone()
                return result[0] if result else 0

        except Exception as e:
            print(f"Error getting recipe usage count: {e}")
            return 0

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

    def add_recipe_to_meal(self, recipe_id, meal_type, servings, date_str, as_recipe=True):
        """Add recipe to a meal

        Args:
            recipe_id: ID of the recipe
            meal_type: breakfast, lunch, dinner, snacks, other
            servings: Number of servings consumed
            date_str: Date in string format
            as_recipe: If True, save as single recipe item; if False, break down into ingredients
        """
        # Convert date format
        date = self._convert_date_format(date_str)

        if as_recipe:
            # Save as a single recipe item
            success = self.food_db.save_recipe_consumption(recipe_id, date, meal_type, servings)
            if success:
                return {
                    'success': True,
                    'message': f'Recipe added to {meal_type}!'
                }
            else:
                return {
                    'success': False,
                    'message': 'Error adding recipe to meal'
                }
        else:
            # Original behavior - break down into ingredients
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
                'message': f'Recipe ingredients added to {meal_type}!'
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

    def update_recipe(self, recipe_id, form_data, create_variation=False):
        """Update an existing recipe or create a variation"""
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

            # Filter out empty ingredient IDs
            valid_ingredients = [(iq_id, quantities[i]) for i, iq_id in enumerate(ingredient_ids) if iq_id and i < len(quantities)]

            if not valid_ingredients:
                return {
                    'success': False,
                    'message': 'At least one valid ingredient is required'
                }

            # Build CSV data for the recipe
            csv_lines = ['ingr,qty,unit,kcal,fats,carbs,fiber,net_carbs,protein']

            for iq_id, quantity_str in valid_ingredients:
                try:
                    # Get ingredient details
                    ingredient = self.food_db.fetch_nutrition(iq_id)
                    quantity = float(quantity_str)

                    # Scale nutrition values
                    scale = quantity / ingredient['qty']

                    csv_line = f"{ingredient['ingredient']},{quantity},{ingredient['unit']}," \
                             f"{ingredient['kcal'] * scale},{ingredient['fat'] * scale}," \
                             f"{ingredient['carb'] * scale},{ingredient['fiber'] * scale}," \
                             f"{ingredient['net_carb'] * scale},{ingredient['protein'] * scale}"
                    csv_lines.append(csv_line)
                except (ValueError, TypeError, KeyError) as e:
                    print(f"Error processing ingredient {iq_id}: {e}")
                    continue

            if len(csv_lines) <= 1:  # Only header line
                return {
                    'success': False,
                    'message': 'No valid ingredients could be processed'
                }

            csv_data = '\n'.join(csv_lines)
            date = datetime.now().strftime('%Y-%m-%d')

            if create_variation:
                # Create a new recipe as variation with unique name
                variation_name = self._generate_unique_variation_name(recipe_name)
                result = self.food_db.save_recipe(date, variation_name, servings, csv_data)

                if isinstance(result, list):
                    return {
                        'success': True,
                        'message': f'Recipe variation "{variation_name}" created successfully!',
                        'is_variation': True
                    }
                else:
                    return {
                        'success': False,
                        'message': f'Error creating recipe variation: {result}'
                    }
            else:
                # Update the existing recipe
                result = self.food_db.update_recipe(recipe_id, recipe_name, servings, csv_data)

                if result:
                    return {
                        'success': True,
                        'message': f'Recipe "{recipe_name}" updated successfully!',
                        'is_variation': False
                    }
                else:
                    return {
                        'success': False,
                        'message': 'Error updating recipe'
                    }

        except Exception as e:
            print(f"Error in update_recipe: {e}")
            return {
                'success': False,
                'message': f'Error processing recipe: {str(e)}'
            }

    def _generate_unique_variation_name(self, base_name):
        """Generate a unique variation name"""
        try:
            all_recipes = self.food_db.fetch_all_recipes()
            existing_names = {recipe['recipe_name'].lower() for recipe in all_recipes}

            # Try different variation patterns
            for i in range(2, 100):  # v2, v3, v4, etc.
                variation_name = f"{base_name} (v{i})"
                if variation_name.lower() not in existing_names:
                    return variation_name

            # If all numbered variations exist, use timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            return f"{base_name} (var_{timestamp})"

        except Exception as e:
            print(f"Error generating variation name: {e}")
            # Fallback to timestamp-based name
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            return f"{base_name} (var_{timestamp})"
