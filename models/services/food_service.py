from models.food import FoodDatabase
import pandas as pd
import io

class FoodService:
    def __init__(self):
        self.food_db = FoodDatabase()

    def get_all_foods_with_favorites(self):
        """Get all foods with favorite status"""
        foods = self.food_db.fetch_all_nutrition()
        favorite_ids = self.food_db.get_favorites()

        # Add favorite status to each food
        for food in foods:
            # Get ingredient_id from ingredient_quantity_id
            ingredient_id, _ = self.food_db.get_unit_ingredient_from_iq(food['id'])
            food['is_favorite'] = ingredient_id in favorite_ids
            food['ingredient_id'] = ingredient_id

        return foods

    def toggle_favorite(self, ingredient_id):
        """Toggle favorite status for an ingredient"""
        is_favorited = self.food_db.toggle_favorite(ingredient_id)

        if is_favorited is not None:
            message = "Added to favorites!" if is_favorited else "Removed from favorites!"
            return {
                'success': True,
                'is_favorited': is_favorited,
                'message': message
            }
        else:
            return {
                'success': False,
                'error': 'Error toggling favorite'
            }

    def add_food(self, food_data):
        """Add a new food to the database"""
        try:
            # Prepare data for CSV format expected by save_to_database
            ingredient_obj = {
                "qty": food_data['quantity'],
                "unit": food_data['unit'],
                "ingr": food_data['food_name'],
                "carbs": food_data['carbs'],
                "fats": food_data['fat'],
                "protein": food_data['protein'],
                "net_carbs": float(food_data['carbs']) - float(food_data.get('fiber', 0)),
                "fiber": food_data.get('fiber', 0),
                "kcal": food_data['calories']
            }

            # Convert to DataFrame and then CSV
            df = pd.DataFrame([ingredient_obj])
            csv_data = df.to_csv(index=False)

            # Save to database
            result = self.food_db.save_to_database(csv_data)

            if result:
                return {
                    'success': True,
                    'message': 'Food added successfully!'
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to add food'
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def update_food(self, iq_id, food_data):
        """Update an existing food"""
        try:
            updated_nutrition = {
                "qty": food_data['quantity'],
                "carb": food_data['carbs'],
                "fat": food_data['fat'],
                "protein": food_data['protein'],
                "net_carb": float(food_data['carbs']) - float(food_data.get('fiber', 0)),
                "fiber": food_data.get('fiber', 0),
                "kcal": food_data['calories']
            }

            self.food_db.update_nutrition(iq_id, updated_nutrition)

            return {
                'success': True,
                'message': 'Food updated successfully!'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def delete_food(self, iq_id):
        """Delete a food from the database"""
        try:
            self.food_db.delete_ingredient_qty(iq_id)

            return {
                'success': True,
                'message': 'Food deleted successfully!'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def get_food_details(self, iq_id):
        """Get details of a specific food"""
        try:
            nutrition = self.food_db.fetch_nutrition(iq_id)
            if nutrition:
                return {
                    'success': True,
                    'food': nutrition
                }
            else:
                return {
                    'success': False,
                    'error': 'Food not found'
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
