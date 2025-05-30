from models.food import FoodDatabase

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
