import sqlite3

# Connect to the database (this will create a new file named "database.db")
conn = sqlite3.connect('database.db')
cursor = conn.cursor()
# Create the Recipe table
cursor.execute('''
CREATE TABLE Recipe (
    recipe_id INTEGER PRIMARY KEY,
    recipe_name VARCHAR(255) NOT NULL UNIQUE,
    recipe_date DATE NOT NULL,
    servings TINYINT NOT NULL
);
''')
# Create the Recipe table
cursor.execute('''
CREATE TABLE Recipe_Ingredients (
    recipe_id INTEGER,
    ingredient_quantity_id INTEGER,
    FOREIGN KEY (recipe_id) REFERENCES Recipe(recipe_id) ON DELETE CASCADE,
    FOREIGN KEY (ingredient_quantity_id) REFERENCES Ingredient_Quantity(ingredient_quantity_id),
    PRIMARY KEY (recipe_id, ingredient_quantity_id)
);
''')
# Create the MuscleGroup table
# cursor.execute('''
# CREATE TABLE MuscleGroup (
#     ID INTEGER PRIMARY KEY AUTOINCREMENT,
#     Name TEXT NOT NULL
# );
# ''')
#
# # Create the Workout table
# cursor.execute('''
# CREATE TABLE Workout (
#     ID INTEGER PRIMARY KEY AUTOINCREMENT,
#     Name TEXT NOT NULL,
#     Date DATE NOT NULL
# );
# ''')
#
# # Create the Exercise table
# cursor.execute('''
# CREATE TABLE Exercise (
#     ID INTEGER PRIMARY KEY AUTOINCREMENT,
#     Name TEXT NOT NULL,
#     MuscleGroupID INTEGER,
#     FOREIGN KEY (MuscleGroupID) REFERENCES MuscleGroup(ID)
# );
# ''')
#
# # Create the Sets table
# cursor.execute('''
# CREATE TABLE Sets (
#     ID INTEGER PRIMARY KEY AUTOINCREMENT,
#     ExerciseID INTEGER,
#     WorkoutID INTEGER,
#     SetNumber INTEGER NOT NULL,
#     Load REAL NOT NULL,
#     Reps INTEGER NOT NULL,
#     FOREIGN KEY (ExerciseID) REFERENCES Exercise(ID),
#     FOREIGN KEY (WorkoutID) REFERENCES Workout(ID)
# );
# ''')
#
# # Create the workout_highlights table
# cursor.execute('''
# CREATE TABLE workout_highlights (
#     id INTEGER PRIMARY KEY,
#     workout_id INTEGER REFERENCES Workout(ID),
#     highlight_text TEXT,
#     date DATE
# );
# ''')
#
#
# # Create the Unit table
# cursor.execute('''
# CREATE TABLE Unit (
#     unit_id INTEGER PRIMARY KEY,
#     unit_name VARCHAR(255) NOT NULL UNIQUE
# );
# ''')
#
# # Create the Ingredient table
# cursor.execute('''
# CREATE TABLE Ingredient (
#     ingredient_id INTEGER PRIMARY KEY,
#     ingredient_name VARCHAR(255) NOT NULL UNIQUE
# );
# ''')
#
# # Create the Ingredient_Quantity table
# cursor.execute('''
# CREATE TABLE Ingredient_Quantity (
#    ingredient_quantity_id INTEGER PRIMARY KEY AUTOINCREMENT,
#     quantity FLOAT NOT NULL,
#     ingredient_id INTEGER,
#     unit_id INTEGER,
#     FOREIGN KEY (ingredient_id) REFERENCES Ingredient(ingredient_id),
#     FOREIGN KEY (unit_id) REFERENCES Unit(unit_id),
#     UNIQUE (quantity, ingredient_id, unit_id)
# );
# ''')
#
# # Create the Nutrition table
# cursor.execute('''
# CREATE TABLE Nutrition (
#     ingredient_id INTEGER,
#     unit_id INTEGER,
#     kcal FLOAT NOT NULL,
#     fat FLOAT NOT NULL,
#     carb FLOAT NOT NULL,
#     fiber FLOAT NOT NULL,
#     net_carb FLOAT NOT NULL,
#     protein FLOAT NOT NULL,
#     FOREIGN KEY (ingredient_id) REFERENCES Ingredient(ingredient_id),
#     FOREIGN KEY (unit_id) REFERENCES Unit(unit_id),
#     PRIMARY KEY (ingredient_id, unit_id),
#     UNIQUE (ingredient_id, unit_id)
# );
# ''')
#
# # Create the Daily_Consumption table
# cursor.execute('''
# CREATE TABLE Consumption (
#     consumption_id INTEGER PRIMARY KEY,
#     consumption_date DATE NOT NULL DEFAULT (strftime('%d.%m.%Y', 'now')),
#     ingredient_quantity_id INTEGER,
#     ingredient_quantity_portions INTEGER DEFAULT 1,
#     FOREIGN KEY (ingredient_quantity_id) REFERENCES Ingredient_Quantity(ingredient_quantity_id),
#     UNIQUE (consumption_date, ingredient_quantity_id)
# );
# ''')

conn.commit()
conn.close()

print("Database and tables created successfully!")
