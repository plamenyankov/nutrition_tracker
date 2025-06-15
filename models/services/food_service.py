from models.food import FoodDatabase
import pandas as pd
import io
import time

class FoodService:
    def __init__(self):
        self.food_db = FoodDatabase()
        self._cache_timestamp = 0
        self._cached_foods = None
        self._cache_duration = 300  # 5 minutes cache

    def _is_cache_valid(self):
        """Check if cache is still valid"""
        return (time.time() - self._cache_timestamp) < self._cache_duration

    def get_all_foods_with_favorites(self, use_cache=True):
        """Get all foods with favorite status - optimized with caching"""
        if use_cache and self._cached_foods and self._is_cache_valid():
            return self._cached_foods

        try:
            # Use optimized query that joins favorites in a single database call
            foods = self._get_foods_with_favorites_optimized()

            if use_cache:
                self._cached_foods = foods
                self._cache_timestamp = time.time()

            return foods
        except Exception as e:
            print(f"Error fetching foods: {e}")
            # Fallback to original method
            return self._get_foods_with_favorites_fallback()

    def _get_foods_with_favorites_optimized(self):
        """Optimized query to get foods with favorites in single database call"""
        with self.food_db.connection_manager.get_connection() as conn:
            cursor = conn.cursor()

            if self.food_db.connection_manager.use_mysql:
                query = """
                SELECT
                    iq.ingredient_quantity_id as id,
                    iq.quantity as qty,
                    U.unit_name as unit,
                    I.ingredient_name as ingredient,
                    ROUND(iq.quantity * N.kcal, 2) as kcal,
                    ROUND(iq.quantity * N.fat, 2) as fat,
                    ROUND(iq.quantity * N.carb, 2) as carb,
                    ROUND(iq.quantity * N.fiber, 2) as fiber,
                    ROUND(iq.quantity * N.net_carb, 2) as net_carb,
                    ROUND(iq.quantity * N.protein, 2) as protein,
                    I.ingredient_id,
                    CASE WHEN F.ingredient_id IS NOT NULL THEN 1 ELSE 0 END as is_favorite
                FROM Ingredient_Quantity iq
                LEFT JOIN Ingredient I ON I.ingredient_id = iq.ingredient_id
                LEFT JOIN Unit U ON U.unit_id = iq.unit_id
                LEFT JOIN Nutrition N ON I.ingredient_id = N.ingredient_id AND U.unit_id = N.unit_id
                LEFT JOIN Favorites F ON I.ingredient_id = F.ingredient_id
                ORDER BY iq.ingredient_quantity_id DESC
                LIMIT 1000
                """
            else:
                query = """
                SELECT
                    iq.ingredient_quantity_id as id,
                    iq.quantity as qty,
                    U.unit_name as unit,
                    I.ingredient_name as ingredient,
                    ROUND(iq.quantity * N.kcal, 2) as kcal,
                    ROUND(iq.quantity * N.fat, 2) as fat,
                    ROUND(iq.quantity * N.carb, 2) as carb,
                    ROUND(iq.quantity * N.fiber, 2) as fiber,
                    ROUND(iq.quantity * N.net_carb, 2) as net_carb,
                    ROUND(iq.quantity * N.protein, 2) as protein,
                    I.ingredient_id,
                    CASE WHEN F.ingredient_id IS NOT NULL THEN 1 ELSE 0 END as is_favorite
                FROM Ingredient_Quantity iq
                LEFT JOIN Ingredient I ON I.ingredient_id = iq.ingredient_id
                LEFT JOIN Unit U ON U.unit_id = iq.unit_id
                LEFT JOIN Nutrition N ON I.ingredient_id = N.ingredient_id AND U.unit_id = N.unit_id
                LEFT JOIN Favorites F ON I.ingredient_id = F.ingredient_id
                ORDER BY iq.ingredient_quantity_id DESC
                LIMIT 1000
                """

            cursor.execute(query)
            results = cursor.fetchall()

            # Convert to list of dictionaries
            foods = []
            for row in results:
                foods.append({
                    "id": row[0],
                    "qty": row[1] or 0,
                    "unit": row[2] or "",
                    "ingredient": row[3] or "",
                    "kcal": row[4] or 0,
                    "fat": row[5] or 0,
                    "carb": row[6] or 0,
                    "fiber": row[7] or 0,
                    "net_carb": row[8] or 0,
                    "protein": row[9] or 0,
                    "ingredient_id": row[10],
                    "is_favorite": bool(row[11])
                })

            return foods

    def _get_foods_with_favorites_fallback(self):
        """Fallback method using original approach"""
        foods = self.food_db.fetch_all_nutrition()
        favorite_ids = self.food_db.get_favorites()

        # Add favorite status to each food
        for food in foods:
            try:
                # Get ingredient_id from ingredient_quantity_id
                ingredient_id, _ = self.food_db.get_unit_ingredient_from_iq(food['id'])
                food['is_favorite'] = ingredient_id in favorite_ids
                food['ingredient_id'] = ingredient_id
            except:
                food['is_favorite'] = False
                food['ingredient_id'] = None

        return foods

    def invalidate_cache(self):
        """Invalidate the foods cache"""
        self._cached_foods = None
        self._cache_timestamp = 0

    def toggle_favorite(self, ingredient_id):
        """Toggle favorite status for an ingredient"""
        try:
            is_favorited = self.food_db.toggle_favorite(ingredient_id)

            # Invalidate cache when favorites change
            self.invalidate_cache()

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
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def add_food(self, food_data):
        """Add a new food to the database"""
        try:
            # Validate required fields
            required_fields = ['quantity', 'unit', 'food_name', 'carbs', 'fat', 'protein', 'calories']
            for field in required_fields:
                if not food_data.get(field):
                    return {
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }

            # Prepare data for CSV format expected by save_to_database
            ingredient_obj = {
                "qty": float(food_data['quantity']),
                "unit": food_data['unit'].strip(),
                "ingr": food_data['food_name'].strip(),
                "carbs": float(food_data['carbs']),
                "fats": float(food_data['fat']),
                "protein": float(food_data['protein']),
                "net_carbs": float(food_data['carbs']) - float(food_data.get('fiber', 0)),
                "fiber": float(food_data.get('fiber', 0)),
                "kcal": float(food_data['calories'])
            }

            # Convert to DataFrame and then CSV
            df = pd.DataFrame([ingredient_obj])
            csv_data = df.to_csv(index=False)

            # Save to database
            result = self.food_db.save_to_database(csv_data)

            # Invalidate cache when new food is added
            self.invalidate_cache()

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

        except ValueError as e:
            return {
                'success': False,
                'error': f'Invalid numeric value: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def update_food(self, iq_id, food_data):
        """Update an existing food"""
        try:
            # Validate required fields
            required_fields = ['quantity', 'carbs', 'fat', 'protein', 'calories']
            for field in required_fields:
                if not food_data.get(field):
                    return {
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }

            updated_nutrition = {
                "qty": float(food_data['quantity']),
                "carb": float(food_data['carbs']),
                "fat": float(food_data['fat']),
                "protein": float(food_data['protein']),
                "net_carb": float(food_data['carbs']) - float(food_data.get('fiber', 0)),
                "fiber": float(food_data.get('fiber', 0)),
                "kcal": float(food_data['calories'])
            }

            self.food_db.update_nutrition(iq_id, updated_nutrition)

            # Invalidate cache when food is updated
            self.invalidate_cache()

            return {
                'success': True,
                'message': 'Food updated successfully!'
            }

        except ValueError as e:
            return {
                'success': False,
                'error': f'Invalid numeric value: {str(e)}'
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

            # Invalidate cache when food is deleted
            self.invalidate_cache()

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
                    'data': nutrition
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

    def get_foods_paginated(self, page=1, per_page=24, search='', filters=None):
        """Get paginated foods with search and filters"""
        if filters is None:
            filters = {}

        try:
            with self.food_db.connection_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Build WHERE clause
                where_conditions = []
                params = []

                if search:
                    where_conditions.append("I.ingredient_name LIKE %s" if self.food_db.connection_manager.use_mysql else "I.ingredient_name LIKE ?")
                    params.append(f'%{search}%')

                if filters.get('favorites_only'):
                    where_conditions.append("F.ingredient_id IS NOT NULL")

                if filters.get('min_calories'):
                    where_conditions.append("ROUND(iq.quantity * N.kcal, 2) >= %s" if self.food_db.connection_manager.use_mysql else "ROUND(iq.quantity * N.kcal, 2) >= ?")
                    params.append(filters['min_calories'])

                if filters.get('max_calories'):
                    where_conditions.append("ROUND(iq.quantity * N.kcal, 2) <= %s" if self.food_db.connection_manager.use_mysql else "ROUND(iq.quantity * N.kcal, 2) <= ?")
                    params.append(filters['max_calories'])

                if filters.get('min_protein'):
                    where_conditions.append("ROUND(iq.quantity * N.protein, 2) >= %s" if self.food_db.connection_manager.use_mysql else "ROUND(iq.quantity * N.protein, 2) >= ?")
                    params.append(filters['min_protein'])

                if filters.get('max_protein'):
                    where_conditions.append("ROUND(iq.quantity * N.protein, 2) <= %s" if self.food_db.connection_manager.use_mysql else "ROUND(iq.quantity * N.protein, 2) <= ?")
                    params.append(filters['max_protein'])

                where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""

                # Count total items
                count_query = f"""
                SELECT COUNT(*)
                FROM Ingredient_Quantity iq
                LEFT JOIN Ingredient I ON I.ingredient_id = iq.ingredient_id
                LEFT JOIN Unit U ON U.unit_id = iq.unit_id
                LEFT JOIN Nutrition N ON I.ingredient_id = N.ingredient_id AND U.unit_id = N.unit_id
                LEFT JOIN Favorites F ON I.ingredient_id = F.ingredient_id
                {where_clause}
                """

                cursor.execute(count_query, params)
                total_count = cursor.fetchone()[0]

                # Get paginated data
                offset = (page - 1) * per_page

                if self.food_db.connection_manager.use_mysql:
                    data_query = f"""
                    SELECT
                        iq.ingredient_quantity_id as id,
                        iq.quantity as qty,
                        U.unit_name as unit,
                        I.ingredient_name as ingredient,
                        ROUND(iq.quantity * N.kcal, 2) as kcal,
                        ROUND(iq.quantity * N.fat, 2) as fat,
                        ROUND(iq.quantity * N.carb, 2) as carb,
                        ROUND(iq.quantity * N.fiber, 2) as fiber,
                        ROUND(iq.quantity * N.net_carb, 2) as net_carb,
                        ROUND(iq.quantity * N.protein, 2) as protein,
                        I.ingredient_id,
                        CASE WHEN F.ingredient_id IS NOT NULL THEN 1 ELSE 0 END as is_favorite
                    FROM Ingredient_Quantity iq
                    LEFT JOIN Ingredient I ON I.ingredient_id = iq.ingredient_id
                    LEFT JOIN Unit U ON U.unit_id = iq.unit_id
                    LEFT JOIN Nutrition N ON I.ingredient_id = N.ingredient_id AND U.unit_id = N.unit_id
                    LEFT JOIN Favorites F ON I.ingredient_id = F.ingredient_id
                    {where_clause}
                    ORDER BY iq.ingredient_quantity_id DESC
                    LIMIT %s OFFSET %s
                    """
                    cursor.execute(data_query, params + [per_page, offset])
                else:
                    data_query = f"""
                    SELECT
                        iq.ingredient_quantity_id as id,
                        iq.quantity as qty,
                        U.unit_name as unit,
                        I.ingredient_name as ingredient,
                        ROUND(iq.quantity * N.kcal, 2) as kcal,
                        ROUND(iq.quantity * N.fat, 2) as fat,
                        ROUND(iq.quantity * N.carb, 2) as carb,
                        ROUND(iq.quantity * N.fiber, 2) as fiber,
                        ROUND(iq.quantity * N.net_carb, 2) as net_carb,
                        ROUND(iq.quantity * N.protein, 2) as protein,
                        I.ingredient_id,
                        CASE WHEN F.ingredient_id IS NOT NULL THEN 1 ELSE 0 END as is_favorite
                    FROM Ingredient_Quantity iq
                    LEFT JOIN Ingredient I ON I.ingredient_id = iq.ingredient_id
                    LEFT JOIN Unit U ON U.unit_id = iq.unit_id
                    LEFT JOIN Nutrition N ON I.ingredient_id = N.ingredient_id AND U.unit_id = N.unit_id
                    LEFT JOIN Favorites F ON I.ingredient_id = F.ingredient_id
                    {where_clause}
                    ORDER BY iq.ingredient_quantity_id DESC
                    LIMIT ? OFFSET ?
                    """
                    cursor.execute(data_query, params + [per_page, offset])

                results = cursor.fetchall()

                # Convert to list of dictionaries
                foods = []
                for row in results:
                    foods.append({
                        "id": row[0],
                        "qty": row[1] or 0,
                        "unit": row[2] or "",
                        "ingredient": row[3] or "",
                        "kcal": row[4] or 0,
                        "fat": row[5] or 0,
                        "carb": row[6] or 0,
                        "fiber": row[7] or 0,
                        "net_carb": row[8] or 0,
                        "protein": row[9] or 0,
                        "ingredient_id": row[10],
                        "is_favorite": bool(row[11])
                    })

                return {
                    'success': True,
                    'foods': foods,
                    'total': total_count,
                    'page': page,
                    'per_page': per_page,
                    'total_pages': (total_count + per_page - 1) // per_page
                }

        except Exception as e:
            print(f"Error in get_foods_paginated: {e}")
            return {
                'success': False,
                'error': str(e),
                'foods': [],
                'total': 0
            }
