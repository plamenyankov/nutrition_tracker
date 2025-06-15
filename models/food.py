import os
from models.database.connection_manager import DatabaseConnectionManager

# Use environment variable for database path (for backward compatibility)
db_path = os.getenv('DATABASE_PATH', 'database.db')
# Convert to absolute path if needed
if not db_path.startswith('/'):
    db_path = os.path.abspath(db_path)
DATABASE_PATH = db_path


# noinspection SqlNoDataSourceInspection
class FoodDatabase:

    def __init__(self):
        self.connection_manager = DatabaseConnectionManager(use_mysql=True)

    def close(self):
        # DatabaseConnectionManager doesn't need explicit closing
        pass

    def save_unit(self, data):
        with self.connection_manager.get_connection() as conn:
            cursor = conn.cursor()
            if self.connection_manager.use_mysql:
                cursor.execute('INSERT IGNORE INTO Unit (unit_name) VALUES (%s)', (data,))
                cursor.execute('SELECT unit_id FROM Unit WHERE unit_name = %s', (data,))
            else:
                cursor.execute('INSERT OR IGNORE INTO Unit (unit_name) VALUES (?)', (data,))
                cursor.execute('SELECT unit_id FROM Unit WHERE unit_name = ?', (data,))

            unit_id = cursor.fetchone()
            if unit_id:
                return unit_id[0]

    def save_ingredient(self, data):
        with self.connection_manager.get_connection() as conn:
            cursor = conn.cursor()
            if self.connection_manager.use_mysql:
                cursor.execute('INSERT IGNORE INTO Ingredient (ingredient_name) VALUES (%s)', (data,))
                cursor.execute('SELECT ingredient_id FROM Ingredient WHERE ingredient_name = %s', (data,))
            else:
                cursor.execute('INSERT OR IGNORE INTO Ingredient (ingredient_name) VALUES (?)', (data,))
                cursor.execute('SELECT ingredient_id FROM Ingredient WHERE ingredient_name = ?', (data,))

            ingredient_id = cursor.fetchone()
            if ingredient_id:
                return ingredient_id[0]

    def save_ingredient_qty(self, quantity, ingredient_id, unit_id, serv=None):
        if serv is not None:
            quantity = float(quantity)/float(serv)

        with self.connection_manager.get_connection() as conn:
            cursor = conn.cursor()
            if self.connection_manager.use_mysql:
                # First check if it already exists
                cursor.execute('SELECT ingredient_quantity_id FROM Ingredient_Quantity WHERE ingredient_id=%s AND unit_id=%s AND quantity=%s', (ingredient_id, unit_id, quantity))
                existing = cursor.fetchone()
                if existing:
                    return existing[0]

                # Insert new record
                cursor.execute('INSERT INTO Ingredient_Quantity (quantity, ingredient_id, unit_id) VALUES (%s,%s,%s)', (quantity, ingredient_id, unit_id,))
                conn.commit()

                # Get the inserted ID
                cursor.execute('SELECT LAST_INSERT_ID()')
                ingredient_quantity_id = cursor.fetchone()[0]
                return ingredient_quantity_id
            else:
                cursor.execute('INSERT OR IGNORE INTO Ingredient_Quantity (quantity, ingredient_id, unit_id) VALUES (?,?,?)', (quantity, ingredient_id, unit_id,))
                cursor.execute('SELECT ingredient_quantity_id FROM Ingredient_Quantity WHERE ingredient_id=? AND unit_id=? AND quantity=?', (ingredient_id, unit_id, quantity))
                ingredient_quantity_id = cursor.fetchone()
                if ingredient_quantity_id:
                    return ingredient_quantity_id[0]

    def save_nutrition(self, ingredient_id, unit_id, kcal, fat, carb, fiber, net_carb, protein):
        with self.connection_manager.get_connection() as conn:
            cursor = conn.cursor()
            if self.connection_manager.use_mysql:
                cursor.execute('INSERT IGNORE INTO Nutrition (ingredient_id, unit_id, kcal, fat, carb, fiber, net_carb, protein) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)', (ingredient_id, unit_id, kcal, fat, carb, fiber, net_carb, protein,))
                cursor.execute('SELECT * FROM Nutrition WHERE ingredient_id=%s AND unit_id=%s', (ingredient_id, unit_id,))
            else:
                cursor.execute('INSERT OR IGNORE INTO Nutrition (ingredient_id, unit_id, kcal, fat, carb, fiber, net_carb, protein) VALUES (?,?,?,?,?,?,?,?)', (ingredient_id, unit_id, kcal, fat, carb, fiber, net_carb, protein,))
                cursor.execute('SELECT * FROM Nutrition WHERE ingredient_id=? AND unit_id=?', (ingredient_id, unit_id,))

            nutrition = cursor.fetchone()
            if nutrition:
                return nutrition[0]

    def save_consumption(self, date, ingredient_quantity_id, meal_type='other'):
        with self.connection_manager.get_connection() as conn:
            cursor = conn.cursor()
            if self.connection_manager.use_mysql:
                cursor.execute('SELECT COUNT(*) cnt FROM Consumption WHERE ingredient_quantity_id = %s AND consumption_date = %s AND meal_type = %s', (ingredient_quantity_id, date, meal_type))
                cnt = cursor.fetchone()[0]
                if cnt:
                    cursor.execute('UPDATE Consumption SET ingredient_quantity_portions = ingredient_quantity_portions + 1 WHERE ingredient_quantity_id = %s AND consumption_date = %s AND meal_type = %s', (ingredient_quantity_id, date, meal_type))
                else:
                    cursor.execute('INSERT INTO Consumption (consumption_date, ingredient_quantity_id, ingredient_quantity_portions, meal_type) VALUES (%s,%s,%s,%s)', (date, ingredient_quantity_id, 1, meal_type))
                    conn.commit()  # Ensure the transaction is committed
            else:
                cursor.execute('SELECT COUNT(*) cnt FROM Consumption WHERE ingredient_quantity_id = ? AND consumption_date = ? AND meal_type = ?', (ingredient_quantity_id, date, meal_type))
                cnt = cursor.fetchone()[0]
                if cnt:
                    cursor.execute('UPDATE Consumption SET ingredient_quantity_portions = ingredient_quantity_portions + 1 WHERE ingredient_quantity_id = ? AND consumption_date = ? AND meal_type = ?', (ingredient_quantity_id, date, meal_type))
                else:
                    cursor.execute('INSERT INTO Consumption (consumption_date, ingredient_quantity_id, ingredient_quantity_portions, meal_type) VALUES (?,?,?,?)', (date, ingredient_quantity_id, 1, meal_type))
            return cnt

    def delete_consumption(self, ingredient_id):
        try:
            with self.connection_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Delete from ingredient_quantity
                if self.connection_manager.use_mysql:
                    cursor.execute('DELETE FROM Consumption WHERE consumption_id= %s', (ingredient_id,))
                else:
                    cursor.execute('DELETE FROM Consumption WHERE consumption_id= ?', (ingredient_id,))

                # Ideally, return a success message or status
                return "Deletion successful"

        except Exception as e:
            # Handle the error and perhaps return a meaningful message
            return f"Error: {e}"

    def delete_ingredient(self, ingredient_id):
        try:
            with self.connection_manager.get_connection() as conn:
                cursor = conn.cursor()

                if self.connection_manager.use_mysql:
                    # Delete from ingredient_quantity
                    cursor.execute('DELETE FROM Ingredient_Quantity WHERE ingredient_id= %s', (ingredient_id,))
                    # Delete from ingredient
                    cursor.execute('DELETE FROM Ingredient WHERE ingredient_id= %s', (ingredient_id,))
                    # Delete from Nutrition
                    cursor.execute('DELETE FROM Nutrition WHERE ingredient_id= %s', (ingredient_id,))
                else:
                    # Delete from ingredient_quantity
                    cursor.execute('DELETE FROM Ingredient_Quantity WHERE ingredient_id= ?', (ingredient_id,))
                    # Delete from ingredient
                    cursor.execute('DELETE FROM Ingredient WHERE ingredient_id= ?', (ingredient_id,))
                    # Delete from Nutrition
                    cursor.execute('DELETE FROM Nutrition WHERE ingredient_id= ?', (ingredient_id,))

                # Ideally, return a success message or status
                return "Deletion successful"

        except Exception as e:
            # Handle the error and perhaps return a meaningful message
            return f"Error: {e}"

    def delete_ingredient_qty(self, ingredient_id):
        try:
            with self.connection_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Delete from ingredient_quantity
                if self.connection_manager.use_mysql:
                    cursor.execute('DELETE FROM Ingredient_Quantity WHERE ingredient_quantity_id= %s', (ingredient_id,))
                else:
                    cursor.execute('DELETE FROM Ingredient_Quantity WHERE ingredient_quantity_id= ?', (ingredient_id,))

                # Ideally, return a success message or status
                return "Deletion successful"

        except Exception as e:
            # Handle the error and perhaps return a meaningful message
            return f"Error: {e}"

    def save_recipe_ingredient(self, recipe_id, ingredient_quantity_id):
        with self.connection_manager.get_connection() as conn:
            cursor = conn.cursor()
            if self.connection_manager.use_mysql:
                cursor.execute('INSERT INTO Recipe_Ingredients (recipe_id, ingredient_quantity_id) VALUES (%s,%s)', (recipe_id, ingredient_quantity_id,))
            else:
                cursor.execute('INSERT INTO Recipe_Ingredients (recipe_id, ingredient_quantity_id) VALUES (?,?)', (recipe_id, ingredient_quantity_id,))

            # Ideally, return a success message or status
            return "Added Ingredient successful"

    def converter_base_unit(self, qty, kcal, fats, carbs, fiber, net_carbs, protein):

        qty = float(qty)
        kcal = float(kcal)
        fats = float(fats)
        carbs = float(carbs)
        fiber = float(fiber)
        net_carbs = float(net_carbs)
        protein = float(protein)

        return round(kcal / qty, 4), round(fats / qty, 4), round(carbs / qty, 4), round(fiber / qty, 4), round(
            net_carbs / qty, 4), round(protein / qty, 4)

    def save_to_database(self, data, serv=1):
        lines = data.strip().split("\n")
        headers = lines[0].split(',')
        entries = [dict(zip(headers, line.split(','))) for line in lines[1:]]
        ingredients_qty_list = []

        for entry in entries:
            # Insert into Unit table
            unit_id = self.save_unit(entry['unit'])

            # Insert into Ingredient table
            ingredient_id = self.save_ingredient(entry['ingr'])

            # save ingredient quantity and get the id
            ingredient_quantity_id = self.save_ingredient_qty(entry['qty'], ingredient_id, unit_id, serv)
            ingredients_qty_list.append(ingredient_quantity_id)

            # Convert Nutrition to Base Unit
            kcal, fats, carbs, fiber, net_carbs, protein = self.converter_base_unit(entry['qty'], entry['kcal'], entry['fats'], entry['carbs'], entry['fiber'], entry['net_carbs'], entry['protein'])

            # Save Nutritions
            self.save_nutrition(ingredient_id, unit_id, kcal, fats, carbs, fiber, net_carbs, protein)
        return ingredients_qty_list

    def save_recipe(self, date, recipe, serv, data):
        # 1st Save Ingredients and Use Servings to scale down IQ and Nutrition's
        # 2nd use the IQ_ids to save the ingredients to recipe_ingredients

        try:
            ingredients_qty_list = self.save_to_database(data, serv)

            with self.connection_manager.get_connection() as conn:
                cursor = conn.cursor()
                if self.connection_manager.use_mysql:
                    cursor.execute('INSERT IGNORE INTO Recipe (recipe_name, recipe_date, servings) VALUES (%s,%s,%s)',
                                   (recipe, date, serv,))
                    cursor.execute('SELECT recipe_id FROM Recipe WHERE recipe_name=%s', (recipe,))
                else:
                    cursor.execute('INSERT OR IGNORE INTO Recipe (recipe_name, recipe_date, servings) VALUES (?,?,?)',
                                   (recipe, date, serv,))
                    cursor.execute('SELECT recipe_id FROM Recipe WHERE recipe_name=?', (recipe,))

                recipe_id = cursor.fetchone()[0]

            for ingredient_quantity_id in ingredients_qty_list:
                self.save_recipe_ingredient(recipe_id, ingredient_quantity_id)  # Pass individual ID

            # Ideally, return a success message or status
            return ingredients_qty_list

        except Exception as e:
            # Handle the error and perhaps return a meaningful message
            return f"Error: {e}"

    def update_nutrition(self, iq_id, n):
        kcal, fats, carbs, fiber, net_carbs, protein = self.converter_base_unit(n['qty'], n['kcal'],n['fat'],n['carb'],n['fiber'],n['net_carb'],n['protein'])
        with self.connection_manager.get_connection() as conn:
            cursor = conn.cursor()
            if self.connection_manager.use_mysql:
                query ="""
                UPDATE Nutrition Set kcal=%s, fat=%s, carb=%s, fiber=%s, net_carb=%s, protein=%s
                WHERE ingredient_id=(SELECT ingredient_id FROM Ingredient_Quantity WHERE ingredient_quantity_id=%s)
                AND unit_id=(SELECT unit_id FROM Ingredient_Quantity WHERE ingredient_quantity_id=%s)
                """
                cursor.execute(query,(kcal, fats, carbs, fiber, net_carbs, protein,iq_id,iq_id,))
            else:
                query ="""
                UPDATE Nutrition Set kcal=?, fat=?, carb=?, fiber=?, net_carb=?, protein=?
                WHERE ingredient_id=(SELECT ingredient_id FROM Ingredient_Quantity WHERE ingredient_quantity_id=?)
                AND unit_id=(SELECT unit_id FROM Ingredient_Quantity WHERE ingredient_quantity_id=?)
                """
                cursor.execute(query,(kcal, fats, carbs, fiber, net_carbs, protein,iq_id,iq_id,))

    def fetch_all_nutrition(self):
        with self.connection_manager.get_connection() as conn:
            cursor = conn.cursor()
            query = """SELECT
                    iq.ingredient_quantity_id id,
                    iq.quantity qty,
                    U.unit_name unit,
                    I.ingredient_name ingredient,
                    round(iq.quantity*N.kcal, 2) kcal,
                    round(iq.quantity*N.fat, 2) fat,
                    round(iq.quantity*N.carb, 2) carb,
                    round(iq.quantity*N.fiber, 2) fiber,
                    round(iq.quantity*N.net_carb, 2) net_carb,
                    round(iq.quantity*N.protein, 2) protein
                FROM Ingredient_Quantity iq
                    LEFT JOIN Ingredient I ON I.ingredient_id = iq.ingredient_id
                    LEFT JOIN Unit U ON U.unit_id = iq.unit_id
                    LEFT JOIN Nutrition N ON I.ingredient_id = N.ingredient_id AND U.unit_id = N.unit_id
                ORDER BY iq.ingredient_quantity_id DESC"""
            cursor.execute(query)

            # Fetch all rows
            nutrition = cursor.fetchall()

            # Convert tuple data to list of dictionaries for better readability
            nutrition_data = []
            for nutrition in nutrition:
                nutrition_data.append({
                    "id":nutrition[0],
                    "qty": nutrition[1],
                    "unit": nutrition[2],
                    "ingredient": nutrition[3],
                    "kcal": nutrition[4],
                    "fat": nutrition[5],
                    "carb": nutrition[6],
                    "fiber": nutrition[7],
                    "net_carb": nutrition[8],
                    "protein": nutrition[9],
                })

            return nutrition_data


    def fetch_nutrition(self, iq_id):
        with self.connection_manager.get_connection() as conn:
            cursor = conn.cursor()
            if self.connection_manager.use_mysql:
                query = """SELECT
                        iq.ingredient_quantity_id id,
                        iq.quantity qty,
                        U.unit_name unit,
                        I.ingredient_name ingredient,
                        round(iq.quantity*N.kcal, 2) kcal,
                        round(iq.quantity*N.fat, 2) fat,
                        round(iq.quantity*N.carb, 2) carb,
                        round(iq.quantity*N.fiber, 2) fiber,
                        round(iq.quantity*N.net_carb, 2) net_carb,
                        round(iq.quantity*N.protein, 2) protein
                    FROM Ingredient_Quantity iq
                        LEFT JOIN Ingredient I ON I.ingredient_id = iq.ingredient_id
                        LEFT JOIN Unit U ON U.unit_id = iq.unit_id
                        LEFT JOIN Nutrition N ON I.ingredient_id = N.ingredient_id AND U.unit_id = N.unit_id
                        WHERE iq.ingredient_quantity_id=%s"""
                cursor.execute(query,(iq_id,))
            else:
                query = """SELECT
                        iq.ingredient_quantity_id id,
                        iq.quantity qty,
                        U.unit_name unit,
                        I.ingredient_name ingredient,
                        round(iq.quantity*N.kcal, 2) kcal,
                        round(iq.quantity*N.fat, 2) fat,
                        round(iq.quantity*N.carb, 2) carb,
                        round(iq.quantity*N.fiber, 2) fiber,
                        round(iq.quantity*N.net_carb, 2) net_carb,
                        round(iq.quantity*N.protein, 2) protein
                    FROM Ingredient_Quantity iq
                        LEFT JOIN Ingredient I ON I.ingredient_id = iq.ingredient_id
                        LEFT JOIN Unit U ON U.unit_id = iq.unit_id
                        LEFT JOIN Nutrition N ON I.ingredient_id = N.ingredient_id AND U.unit_id = N.unit_id
                        WHERE iq.ingredient_quantity_id=?"""
                cursor.execute(query,(iq_id,))

            # Fetch all rows
            nutrition = cursor.fetchall()[0]

            nutrition_data = {
                "id":nutrition[0],
                "qty": nutrition[1],
                "unit": nutrition[2],
                "ingredient": nutrition[3],
                "kcal": nutrition[4],
                "fat": nutrition[5],
                "carb": nutrition[6],
                "fiber": nutrition[7],
                "net_carb": nutrition[8],
                "protein": nutrition[9],
            }

            return nutrition_data


    def fetch_all_consumption(self):
        with self.connection_manager.get_connection() as conn:
            cursor = conn.cursor()
            query = """SELECT
                        c.consumption_date date,
                        IQ.quantity*c.ingredient_quantity_portions qty,
                        U.unit_name unit,
                        I.ingredient_name ingredient,
                        round(IQ.quantity*N.kcal*c.ingredient_quantity_portions, 2) kcal,
                        round(IQ.quantity*N.fat*c.ingredient_quantity_portions, 2) fat,
                        round(IQ.quantity*N.carb*c.ingredient_quantity_portions, 2) carb,
                        round(IQ.quantity*N.fiber*c.ingredient_quantity_portions, 2) fiber,
                        round(IQ.quantity*N.net_carb*c.ingredient_quantity_portions, 2) net_carb,
                        round(IQ.quantity*N.protein*c.ingredient_quantity_portions, 2) protein,
                        c.consumption_id consumption_id,
                        c.ingredient_quantity_portions iqp,
                        IQ.ingredient_quantity_id,
                        c.meal_type
                        FROM Consumption c
                    LEFT JOIN Ingredient_Quantity IQ ON IQ.ingredient_quantity_id = c.ingredient_quantity_id
                    LEFT JOIN Unit U ON U.unit_id = IQ.unit_id
                    LEFT JOIN Ingredient I ON I.ingredient_id = IQ.ingredient_id
                    LEFT JOIN Nutrition N ON I.ingredient_id = N.ingredient_id AND N.unit_id = U.unit_id
                    ORDER BY date DESC, meal_type"""

            cursor.execute(query)

            # Fetch all rows
            nutrition = cursor.fetchall()

            # Convert tuple data to list of dictionaries for better readability
            nutrition_data = []
            for nutrition in nutrition:
                nutrition_data.append({
                    "date": nutrition[0],
                    "qty": nutrition[1],
                    "unit": nutrition[2],
                    "ingredient": nutrition[3],
                    "kcal": nutrition[4],
                    "fat": nutrition[5],
                    "carb": nutrition[6],
                    "fiber": nutrition[7],
                    "net_carb": nutrition[8],
                    "protein": nutrition[9],
                    "consumption_id": nutrition[10],
                    "iqp": nutrition[11],
                    "iq_id":nutrition[12],
                    "meal_type": nutrition[13] if len(nutrition) > 13 else 'other'
                })

            return nutrition_data

    def fetch_all_recipes(self):
        with self.connection_manager.get_connection() as conn:
            cursor = conn.cursor()
            query = """SELECT
                            r.recipe_name,
                            r.recipe_date,
                            r.servings,
                            round(sum(N.kcal*IQ.quantity),0) kcal,
                            round(sum(N.fat*IQ.quantity),0) fat,
                            round(sum(N.carb*IQ.quantity),0) carb,
                            round(sum(N.fiber*IQ.quantity),0) fiber,
                            round(sum(N.net_carb*IQ.quantity),0) net_carb,
                            round(sum(N.protein*IQ.quantity),0) protein,
                            r.recipe_id
                         FROM Recipe r LEFT JOIN Recipe_Ingredients RI ON r.recipe_id = RI.recipe_id
                                 LEFT JOIN Ingredient_Quantity IQ ON IQ.ingredient_quantity_id = RI.ingredient_quantity_id
                                 LEFT OUTER JOIN Ingredient I ON I.ingredient_id = IQ.ingredient_id
                                 LEFT JOIN Unit U ON U.unit_id = IQ.unit_id
                                 LEFT JOIN Nutrition N ON IQ.unit_id = N.unit_id AND IQ.ingredient_id = N.ingredient_id
                         GROUP BY r.recipe_id, r.recipe_name, r.recipe_date, r.servings
                         ORDER BY r.recipe_date ASC LIMIT 20"""

            cursor.execute(query)

            # Fetch all rows
            nutrition = cursor.fetchall()

            # Convert tuple data to list of dictionaries for better readability
            nutrition_data = []
            for nutrition in nutrition:
                nutrition_data.append({
                    "recipe_name": nutrition[0],
                    "date": nutrition[1],
                    "serv": nutrition[2],
                    "kcal": nutrition[3],
                    "fat": nutrition[4],
                    "carb": nutrition[5],
                    "fiber": nutrition[6],
                    "net_carb": nutrition[7],
                    "protein": nutrition[8],
                    "recipe_id": nutrition[9]
                })

            return nutrition_data

    def fetch_recipe_ingredients(self, recipe_id):
        with self.connection_manager.get_connection() as conn:
            cursor = conn.cursor()
            if self.connection_manager.use_mysql:
                query ="""
                SELECT ri.ingredient_quantity_id iq
                FROM Recipe r
                LEFT JOIN Recipe_Ingredients ri ON r.recipe_id = ri.recipe_id
                WHERE r.recipe_id=%s
                """
                cursor.execute(query, (recipe_id,))
            else:
                query ="""
                SELECT ri.ingredient_quantity_id iq
                FROM Recipe r
                LEFT JOIN Recipe_Ingredients ri ON r.recipe_id = ri.recipe_id
                WHERE r.recipe_id=?
                """
                cursor.execute(query, (recipe_id,))
            ingredient_ids = cursor.fetchall()
            ingredient_ids_list = []
            for ingredient_id in ingredient_ids:
                ingredient_ids_list.append(ingredient_id[0])

            return ingredient_ids_list

    def get_unit_ingredient_from_iq(self, iq_id):
        with self.connection_manager.get_connection() as conn:
            cursor = conn.cursor()
            if self.connection_manager.use_mysql:
                query ="""
                SELECT
                ingredient_id,
                unit_id
                FROM Ingredient_Quantity
                WHERE ingredient_quantity_id=%s
                """
                cursor.execute(query, (iq_id,))
            else:
                query ="""
                SELECT
                ingredient_id,
                unit_id
                FROM Ingredient_Quantity
                WHERE ingredient_quantity_id=?
                """
                cursor.execute(query, (iq_id,))
            result = cursor.fetchone()
            return result[0], result[1]
    def get_avg_nutrition_consumed(self):
        with self.connection_manager.get_connection() as conn:
            cursor = conn.cursor()
            if self.connection_manager.use_mysql:
                query ="""
                SELECT
                    round(sum(kcal)/count(*),0) kcal,
                    round(sum(fat)/count(*),0) fat,
                    round(sum(carb)/count(*),0) carb,
                    round(sum(fiber)/count(*),0) fiber,
                    round(sum(net_carb)/count(*),0) net_carb,
                    round(sum(protein)/count(*),0) protein,
                    COUNT(*) cnt
                FROM (SELECT
                    c.consumption_date date,
                    round(sum(IQ.quantity*N.kcal*c.ingredient_quantity_portions), 0) kcal,
                    round(sum(IQ.quantity*N.fat*c.ingredient_quantity_portions), 0) fat,
                    round(sum(IQ.quantity*N.carb*c.ingredient_quantity_portions), 0) carb,
                    round(sum(IQ.quantity*N.fiber*c.ingredient_quantity_portions), 0) fiber,
                    round(sum(IQ.quantity*N.net_carb*c.ingredient_quantity_portions), 0) net_carb,
                    round(sum(IQ.quantity*N.protein*c.ingredient_quantity_portions), 0) protein
                    FROM Consumption c
                LEFT JOIN Ingredient_Quantity IQ ON IQ.ingredient_quantity_id = c.ingredient_quantity_id
                LEFT JOIN Unit U ON U.unit_id = IQ.unit_id
                LEFT JOIN Ingredient I ON I.ingredient_id = IQ.ingredient_id
                LEFT JOIN Nutrition N ON I.ingredient_id = N.ingredient_id AND N.unit_id = U.unit_id
                GROUP BY c.consumption_date
                ORDER BY date DESC) AS daily_nutrition
                """
            else:
                query ="""
                SELECT
                    round(sum(kcal)/count(*),0) kcal,
                    round(sum(fat)/count(*),0) fat,
                    round(sum(carb)/count(*),0) carb,
                    round(sum(fiber)/count(*),0) fiber,
                    round(sum(net_carb)/count(*),0) net_carb,
                    round(sum(protein)/count(*),0) protein,
                    COUNT(*) cnt
                FROM (SELECT
                    c.consumption_date date,
                    round(sum(IQ.quantity*N.kcal*c.ingredient_quantity_portions), 0) kcal,
                    round(sum(IQ.quantity*N.fat*c.ingredient_quantity_portions), 0) fat,
                    round(sum(IQ.quantity*N.carb*c.ingredient_quantity_portions), 0) carb,
                    round(sum(IQ.quantity*N.fiber*c.ingredient_quantity_portions), 0) fiber,
                    round(sum(IQ.quantity*N.net_carb*c.ingredient_quantity_portions), 0) net_carb,
                    round(sum(IQ.quantity*N.protein*c.ingredient_quantity_portions), 0) protein
                    FROM Consumption c
                LEFT JOIN Ingredient_Quantity IQ ON IQ.ingredient_quantity_id = c.ingredient_quantity_id
                LEFT JOIN Unit U ON U.unit_id = IQ.unit_id
                LEFT JOIN Ingredient I ON I.ingredient_id = IQ.ingredient_id
                LEFT JOIN Nutrition N ON I.ingredient_id = N.ingredient_id AND N.unit_id = U.unit_id
                GROUP BY c.consumption_date
                ORDER BY date DESC)
                """
            cursor.execute(query)
            result = cursor.fetchone()
            nutrition_data = {
                "kcal": result[0],
                "fat": result[1],
                "carb": result[2],
                "fiber": result[3],
                "net_carb": result[4],
                "protein": result[5],
                "cnt":result[6]
            }

            return nutrition_data

    def delete_recipe(self, recipe_id):
        try:
            with self.connection_manager.get_connection() as conn:
                cursor = conn.cursor()

                if self.connection_manager.use_mysql:
                    # First delete from Recipe_Ingredients
                    cursor.execute('DELETE FROM Recipe_Ingredients WHERE recipe_id = %s', (recipe_id,))
                    # Then delete from Recipe
                    cursor.execute('DELETE FROM Recipe WHERE recipe_id = %s', (recipe_id,))
                else:
                    # First delete from Recipe_Ingredients
                    cursor.execute('DELETE FROM Recipe_Ingredients WHERE recipe_id = ?', (recipe_id,))
                    # Then delete from Recipe
                    cursor.execute('DELETE FROM Recipe WHERE recipe_id = ?', (recipe_id,))

                # Commit the changes
                conn.commit()

                return "Recipe deleted successfully"

        except Exception as e:
            # Handle the error and return a meaningful message
            return f"Error deleting recipe: {e}"

    def toggle_favorite(self, ingredient_id):
        """Toggle favorite status for an ingredient"""
        try:
            with self.connection_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Check if already favorited
                if self.connection_manager.use_mysql:
                    cursor.execute('SELECT favorite_id FROM Favorites WHERE ingredient_id = %s', (ingredient_id,))
                    favorite = cursor.fetchone()

                    if favorite:
                        # Remove from favorites
                        cursor.execute('DELETE FROM Favorites WHERE ingredient_id = %s', (ingredient_id,))
                        return False  # Unfavorited
                    else:
                        # Add to favorites
                        cursor.execute('INSERT INTO Favorites (ingredient_id) VALUES (%s)', (ingredient_id,))
                        return True  # Favorited
                else:
                    cursor.execute('SELECT favorite_id FROM Favorites WHERE ingredient_id = ?', (ingredient_id,))
                    favorite = cursor.fetchone()

                    if favorite:
                        # Remove from favorites
                        cursor.execute('DELETE FROM Favorites WHERE ingredient_id = ?', (ingredient_id,))
                        return False  # Unfavorited
                    else:
                        # Add to favorites
                        cursor.execute('INSERT INTO Favorites (ingredient_id) VALUES (?)', (ingredient_id,))
                        return True  # Favorited

        except Exception as e:
            print(f"Error toggling favorite: {e}")
            return None

    def get_favorites(self):
        """Get all favorite ingredient IDs"""
        try:
            with self.connection_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT ingredient_id FROM Favorites')
                favorites = cursor.fetchall()
                return [f[0] for f in favorites]

        except Exception as e:
            print(f"Error fetching favorites: {e}")
            return []

    def save_recipe_consumption(self, recipe_id, date, meal_type, servings=1):
        """Save recipe consumption as a single meal item"""
        with self.connection_manager.get_connection() as conn:
            cursor = conn.cursor()
            try:
                if self.connection_manager.use_mysql:
                    cursor.execute('''
                        INSERT INTO recipe_consumption
                        (recipe_id, consumption_date, meal_type, servings)
                        VALUES (%s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE servings = VALUES(servings)
                    ''', (recipe_id, date, meal_type, servings))
                else:
                    cursor.execute('''
                        INSERT OR REPLACE INTO recipe_consumption
                        (recipe_id, consumption_date, meal_type, servings)
                        VALUES (?, ?, ?, ?)
                    ''', (recipe_id, date, meal_type, servings))
                return True
            except Exception as e:
                print(f"Error saving recipe consumption: {e}")
                return False

    def fetch_recipe_consumption(self, date=None):
        """Fetch recipe consumption records"""
        with self.connection_manager.get_connection() as conn:
            cursor = conn.cursor()
            if date:
                query = '''
                    SELECT rc.recipe_consumption_id, rc.recipe_id, rc.consumption_date,
                           rc.meal_type, rc.servings, r.recipe_name, r.servings as recipe_servings,
                           r.recipe_id,
                           round(sum(N.kcal*IQ.quantity*rc.servings/r.servings),0) kcal,
                           round(sum(N.fat*IQ.quantity*rc.servings/r.servings),0) fat,
                           round(sum(N.carb*IQ.quantity*rc.servings/r.servings),0) carb,
                           round(sum(N.protein*IQ.quantity*rc.servings/r.servings),0) protein
                    FROM recipe_consumption rc
                    JOIN Recipe r ON rc.recipe_id = r.recipe_id
                    LEFT JOIN Recipe_Ingredients RI ON r.recipe_id = RI.recipe_id
                    LEFT JOIN Ingredient_Quantity IQ ON IQ.ingredient_quantity_id = RI.ingredient_quantity_id
                    LEFT JOIN Unit U ON U.unit_id = IQ.unit_id
                    LEFT JOIN Ingredient I ON I.ingredient_id = IQ.ingredient_id
                    LEFT JOIN Nutrition N ON IQ.unit_id = N.unit_id AND IQ.ingredient_id = N.ingredient_id
                    WHERE rc.consumption_date = %s
                    GROUP BY rc.recipe_consumption_id
                ''' if self.connection_manager.use_mysql else '''
                    SELECT rc.recipe_consumption_id, rc.recipe_id, rc.consumption_date,
                           rc.meal_type, rc.servings, r.recipe_name, r.servings as recipe_servings,
                           r.recipe_id,
                           round(sum(N.kcal*IQ.quantity*rc.servings/r.servings),0) kcal,
                           round(sum(N.fat*IQ.quantity*rc.servings/r.servings),0) fat,
                           round(sum(N.carb*IQ.quantity*rc.servings/r.servings),0) carb,
                           round(sum(N.protein*IQ.quantity*rc.servings/r.servings),0) protein
                    FROM recipe_consumption rc
                    JOIN Recipe r ON rc.recipe_id = r.recipe_id
                    LEFT JOIN Recipe_Ingredients RI ON r.recipe_id = RI.recipe_id
                    LEFT JOIN Ingredient_Quantity IQ ON IQ.ingredient_quantity_id = RI.ingredient_quantity_id
                    LEFT JOIN Unit U ON U.unit_id = IQ.unit_id
                    LEFT JOIN Ingredient I ON I.ingredient_id = IQ.ingredient_id
                    LEFT JOIN Nutrition N ON IQ.unit_id = N.unit_id AND IQ.ingredient_id = N.ingredient_id
                    WHERE rc.consumption_date = ?
                    GROUP BY rc.recipe_consumption_id
                '''
                cursor.execute(query, (date,))
            else:
                query = '''
                    SELECT rc.recipe_consumption_id, rc.recipe_id, rc.consumption_date,
                           rc.meal_type, rc.servings, r.recipe_name, r.servings as recipe_servings,
                           r.recipe_id,
                           round(sum(N.kcal*IQ.quantity*rc.servings/r.servings),0) kcal,
                           round(sum(N.fat*IQ.quantity*rc.servings/r.servings),0) fat,
                           round(sum(N.carb*IQ.quantity*rc.servings/r.servings),0) carb,
                           round(sum(N.protein*IQ.quantity*rc.servings/r.servings),0) protein
                    FROM recipe_consumption rc
                    JOIN Recipe r ON rc.recipe_id = r.recipe_id
                    LEFT JOIN Recipe_Ingredients RI ON r.recipe_id = RI.recipe_id
                    LEFT JOIN Ingredient_Quantity IQ ON IQ.ingredient_quantity_id = RI.ingredient_quantity_id
                    LEFT JOIN Unit U ON U.unit_id = IQ.unit_id
                    LEFT JOIN Ingredient I ON I.ingredient_id = IQ.ingredient_id
                    LEFT JOIN Nutrition N ON IQ.unit_id = N.unit_id AND IQ.ingredient_id = N.ingredient_id
                    GROUP BY rc.recipe_consumption_id
                    ORDER BY rc.consumption_date DESC
                '''
                cursor.execute(query)

            results = cursor.fetchall()
            return [{
                'recipe_consumption_id': r[0],
                'recipe_id': r[1],
                'date': r[2],
                'meal_type': r[3],
                'servings': r[4],
                'recipe_name': r[5],
                'recipe_servings': r[6],
                'recipe_id': r[7],
                'kcal': r[8],
                'fat': r[9],
                'carb': r[10],
                'protein': r[11]
            } for r in results]

    def delete_recipe_consumption(self, recipe_consumption_id):
        """Delete a recipe consumption record"""
        try:
            with self.connection_manager.get_connection() as conn:
                cursor = conn.cursor()
                if self.connection_manager.use_mysql:
                    cursor.execute('DELETE FROM recipe_consumption WHERE recipe_consumption_id = %s',
                                 (recipe_consumption_id,))
                else:
                    cursor.execute('DELETE FROM recipe_consumption WHERE recipe_consumption_id = ?',
                                 (recipe_consumption_id,))
                return "Deletion successful"
        except Exception as e:
            return f"Error: {e}"
