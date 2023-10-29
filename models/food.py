import sqlite3
import pandas as pd
import math
import numpy as np
DATABASE_PATH = 'sqlite:///../database.db'


# noinspection SqlNoDataSourceInspection
class FoodDatabase:

    def __init__(self):
        self.conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)

    def close(self):
        if self.conn:
            self.conn.close()

    def save_unit(self,data):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute('INSERT OR IGNORE INTO Unit (unit_name) VALUES (?)', (data,))
            unit_id = cursor.execute('SELECT unit_id FROM Unit WHERE unit_name = ?', (data,)).fetchone()
            if unit_id:
                return unit_id[0]

    def save_ingredient(self, data):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute('INSERT OR IGNORE INTO Ingredient (ingredient_name) VALUES (?)', (data,))
            ingredient_id = cursor.execute('SELECT ingredient_id FROM Ingredient WHERE ingredient_name = ?',
                                           (data,)).fetchone()
            if ingredient_id:
                return ingredient_id[0]

    def save_ingredient_quantity(self, quantity, ingredient_id, unit_id):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute('INSERT OR IGNORE INTO Ingredient_Quantity (quantity, ingredient_id, unit_id) VALUES (?,?,?)', (quantity, ingredient_id, unit_id,))
            ingredient_quantity_id = cursor.execute('SELECT ingredient_quantity_id FROM Ingredient_Quantity WHERE ingredient_id=? AND unit_id=?',
                                           (ingredient_id, unit_id,)).fetchone()
            if ingredient_quantity_id:
                return ingredient_quantity_id[0]

    def save_nutrition(self, ingredient_id, unit_id, kcal, fat, carb, fiber, net_carb, protein):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute('INSERT OR IGNORE INTO Nutrition (ingredient_id, unit_id, kcal, fat, carb, fiber, net_carb, protein) VALUES (?,?,?,?,?,?,?,?)',
                           (ingredient_id, unit_id, kcal, fat, carb, fiber, net_carb, protein,))

            nutrition = cursor.execute('SELECT * FROM Nutrition WHERE ingredient_id=? AND unit_id=?',
                                           (ingredient_id, unit_id,)).fetchone()
            if nutrition:
                return nutrition[0]

    def save_consumption(self, date, ingredient_quantity_id):
        with self.conn:
            cursor = self.conn.cursor()
            cnt = cursor.execute('SELECT COUNT(*) cnt FROM Consumption WHERE ingredient_quantity_id = ? AND consumption_date = ?', (ingredient_quantity_id, date,)).fetchone()[0]
            if cnt:
                cursor.execute('UPDATE Consumption SET ingredient_quantity_portions = ingredient_quantity_portions + 1 WHERE ingredient_quantity_id = ? AND consumption_date = ?', (ingredient_quantity_id, date,))
            else:
                cursor.execute('INSERT OR IGNORE INTO Consumption (ingredient_quantity_id, consumption_date) VALUES (?,?)', (ingredient_quantity_id, date,))
            return cnt
    def converter_base_unit(self, qty, kcal, fats, carbs, fiber, net_carbs, protein, serv):

        qty = float(qty)/serv
        kcal = float(kcal)
        fats = float(fats)
        carbs = float(carbs)
        fiber = float(fiber)
        net_carbs = float(net_carbs)
        protein = float(protein)

        return round(kcal/qty,4), round(fats/qty,4), round(carbs/qty,4), round(fiber/qty,4), round(net_carbs/qty,4), round(protein/qty,4)
    def delete_consumption(self, ingredient_id):
        try:
            with self.conn:
                cursor = self.conn.cursor()

                # Delete from ingredient_quantity
                cursor.execute('DELETE FROM Consumption WHERE consumption_id= ?', (ingredient_id,))

                # Commit the changes
                self.conn.commit()

                # Ideally, return a success message or status
                return "Deletion successful"

        except sqlite3.Error as e:
            # Handle the error and perhaps return a meaningful message
            return f"Error: {e}"

        finally:
            if cursor:
                cursor.close()
    def delete_ingredient(self, ingredient_id):
        try:
            with self.conn:
                cursor = self.conn.cursor()

                # Delete from ingredient_quantity
                cursor.execute('DELETE FROM Ingredient_Quantity WHERE ingredient_id= ?', (ingredient_id,))

                # Delete from ingredient
                cursor.execute('DELETE FROM Ingredient WHERE ingredient_id= ?', (ingredient_id,))

                # Delete from Nutrition
                cursor.execute('DELETE FROM Nutrition WHERE ingredient_id= ?', (ingredient_id,))

                # Commit the changes
                self.conn.commit()

                # Ideally, return a success message or status
                return "Deletion successful"

        except sqlite3.Error as e:
            # Handle the error and perhaps return a meaningful message
            return f"Error: {e}"

        finally:
            if cursor:
                cursor.close()

    def save_recipe_ingredient(self, recipe_id, ingredient_quantity_id):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute('INSERT INTO Recipe_Ingredients (recipe_id, ingredient_quantity_id) VALUES (?,?)',
                           (recipe_id, ingredient_quantity_id,))
            # Commit the changes
            self.conn.commit()

            # Ideally, return a success message or status
            return "Added Ingredient successful"
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
            ingredient_quantity_id = self.save_ingredient_quantity(entry['qty'], ingredient_id, unit_id)
            ingredients_qty_list.append(ingredient_quantity_id)
            # Convert Nutrition to Base Unit
            kcal, fats, carbs, fiber, net_carbs, protein = self.converter_base_unit(entry['qty'], entry['kcal'], entry['fats'], entry['carbs'], entry['fiber'], entry['net_carbs'], entry['protein'],serv)
            # Save Nutritions
            nutrition = self.save_nutrition(ingredient_id, unit_id, kcal, fats, carbs, fiber, net_carbs, protein)
        return ingredients_qty_list

    def save_recipe(self, date, recipe, serv, data):
        try:
            ingredients_qty_list = self.save_to_database(data, serv)

            with self.conn:
                cursor = self.conn.cursor()
                cursor.execute('INSERT OR IGNORE INTO Recipe (recipe_name, recipe_date, servings) VALUES (?,?,?)',
                               (recipe, date, serv,))

                # Fetch the recipe_id correctly
                cursor.execute('SELECT recipe_id FROM Recipe WHERE recipe_name=?', (recipe,))
                recipe_id = cursor.fetchone()[0]

                # Commit the changes
                self.conn.commit()

            for ingredient_quantity_id in ingredients_qty_list:
                result = self.save_recipe_ingredient(recipe_id, ingredient_quantity_id)  # Pass individual ID

            # Ideally, return a success message or status
            return ingredients_qty_list

        except sqlite3.Error as e:
            # Handle the error and perhaps return a meaningful message
            return f"Error: {e}"

        finally:
            if cursor:
                cursor.close()

    def fetch_all_nutrition(self):
        with self.conn:
            cursor = self.conn.cursor()
            query = "SELECT * FROM Nutrition n LEFT JOIN Ingredient i ON n.ingredient_id = i.ingredient_id"
            cursor.execute(query)

            # Fetch all rows
            nutrition = cursor.fetchall()

            # Convert tuple data to list of dictionaries for better readability
            nutrition_data = []
            for nutrition in nutrition:
                nutrition_data.append({

                    "ingredient_name": nutrition[9],
                    "ingredient_id": nutrition[8],
                    "unit_id": nutrition[1],
                    "kcal": nutrition[2],
                    "fat": nutrition[3],
                    "carb": nutrition[4],
                    "fiber": nutrition[5],
                    "net_carb": nutrition[6],
                    "protein": nutrition[7]

                })

            return nutrition_data


    def fetch_all_consumption(self):
        with self.conn:
            cursor = self.conn.cursor()
            query = """SELECT                        
                        c.consumption_date date,
                        IQ.quantity qty,
                        U.unit_name unit,
                        I.ingredient_name ingredient,
                        round(IQ.quantity*N.kcal, 2) kcal,
                        round(IQ.quantity*N.fat, 2) fat,
                        round(IQ.quantity*N.carb, 2) carb,
                        round(IQ.quantity*N.fiber, 2) fiber,
                        round(IQ.quantity*N.net_carb, 2) net_carb,
                        round(IQ.quantity*N.protein, 2) protein,
                        c.consumption_id consumption_id
                        FROM Consumption c
                    LEFT JOIN Ingredient_Quantity IQ ON IQ.ingredient_quantity_id = c.ingredient_quantity_id
                    LEFT JOIN Unit U ON U.unit_id = IQ.unit_id
                    LEFT JOIN Ingredient I ON I.ingredient_id = IQ.ingredient_id
                    LEFT JOIN Nutrition N ON I.ingredient_id = N.ingredient_id AND N.unit_id = U.unit_id
                    ORDER BY date ASC"""

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
                    "consumption_id": nutrition[10]
                })

            return nutrition_data

