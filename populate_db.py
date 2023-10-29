import sqlite3

# Connect to the database
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Insert Units
cursor.executemany('INSERT OR IGNORE INTO Unit (unit_name) VALUES (?)', [('large',), ('g',), ('ml',)])

# Insert Ingredients
cursor.executemany('INSERT OR IGNORE INTO Ingredient (ingredient_name) VALUES (?)',
                   [('banana',), ('oats',), ('egg',), ('cocoa powder',), ('milk',)])

# Insert Nutrition Data
nutrition_data = [
    ('banana', 'large', 121, 0.4, 27, 23.9, 31, 1.3),
    ('oats', 'g', 3.89, 0.069, 0.66, 4.8, 1.8, 0.11),
    ('egg', 'large', 72, 5, 0.6, 0.6, 0, 6.3),
    ('cocoa powder', 'g', 3.05, 0.055, 0.6, 1.8, 1.8, 0.11),
    ('milk', 'ml', 0.6, 0.012, 0.048, 4.8, 0, 0.034)
]

for data in nutrition_data:
    ingredient, unit, kcal, fat, carb, fiber, net_carb, protein = data
    cursor.execute('''
    INSERT OR REPLACE INTO Nutrition (ingredient_id, unit_id, kcal, fat, carb, fiber, net_carb, protein) VALUES
    ((SELECT ingredient_id FROM Ingredient WHERE ingredient_name = ?), 
    (SELECT unit_id FROM Unit WHERE unit_name = ?), ?, ?, ?, ?, ?, ?)
    ''', (ingredient, unit, kcal, fat, carb, fiber, net_carb, protein))

# Inserting a sample recipe
cursor.execute("INSERT INTO Recipe (recipe_name, url, recipe_date, servings) VALUES (?, NULL, ?, ?)",
               ('Oats Pancake', '2023-10-26', 1))

# Insert ingredient quantities for the recipe
ingredient_quantities = [
    ('Oats Pancake', 'banana', 'large', 1),
    ('Oats Pancake', 'oats', 'g', 100),
    ('Oats Pancake', 'egg', 'large', 1),
    ('Oats Pancake', 'cocoa powder', 'g', 20),
    ('Oats Pancake', 'milk', 'ml', 100)
]

for data in ingredient_quantities:
    recipe, ingredient, unit, quantity = data
    cursor.execute('''
    INSERT INTO Ingredient_Quantity (recipe_id, ingredient_id, unit_id, quantity) VALUES
    ((SELECT recipe_id FROM Recipe WHERE recipe_name = ?), 
    (SELECT ingredient_id FROM Ingredient WHERE ingredient_name = ?), 
    (SELECT unit_id FROM Unit WHERE unit_name = ?), ?)
    ''', (recipe, ingredient, unit, quantity))

conn.commit()
conn.close()

print("Data populated successfully!")
