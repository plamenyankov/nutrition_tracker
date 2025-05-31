#!/usr/bin/env python3
"""
Initialize database if it doesn't exist.
This script is safe to run multiple times - it won't overwrite existing data.
"""
import os
import sqlite3
from pathlib import Path

DATABASE_PATH = os.getenv('DATABASE_PATH', 'database.db')

def init_database():
    """Initialize database with all required tables if they don't exist."""

    # Check if database exists
    db_exists = Path(DATABASE_PATH).exists()

    if db_exists:
        print(f"Database {DATABASE_PATH} already exists. Checking schema...")
    else:
        print(f"Creating new database at {DATABASE_PATH}...")

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Get existing tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    existing_tables = {row[0] for row in cursor.fetchall()}

    # Create tables only if they don't exist
    tables_to_create = []

    if 'Ingredient' not in existing_tables:
        tables_to_create.append("""
            CREATE TABLE Ingredient (
                ingredient_id INTEGER PRIMARY KEY,
                ingredient_name VARCHAR(255) NOT NULL UNIQUE
            )
        """)

    if 'Unit' not in existing_tables:
        tables_to_create.append("""
            CREATE TABLE Unit (
                unit_id INTEGER PRIMARY KEY,
                unit_name VARCHAR(255) NOT NULL UNIQUE
            )
        """)

    if 'Nutrition' not in existing_tables:
        tables_to_create.append("""
            CREATE TABLE Nutrition (
                ingredient_id INTEGER,
                unit_id INTEGER,
                kcal FLOAT NOT NULL,
                fat FLOAT NOT NULL,
                carb FLOAT NOT NULL,
                fiber FLOAT NOT NULL,
                net_carb FLOAT NOT NULL,
                protein FLOAT NOT NULL,
                FOREIGN KEY (ingredient_id) REFERENCES Ingredient(ingredient_id),
                FOREIGN KEY (unit_id) REFERENCES Unit(unit_id),
                PRIMARY KEY (ingredient_id, unit_id),
                UNIQUE (ingredient_id, unit_id)
            )
        """)

    if 'Ingredient_Quantity' not in existing_tables:
        tables_to_create.append("""
            CREATE TABLE Ingredient_Quantity (
                ingredient_quantity_id INTEGER PRIMARY KEY AUTOINCREMENT,
                quantity FLOAT NOT NULL,
                ingredient_id INTEGER,
                unit_id INTEGER,
                FOREIGN KEY (ingredient_id) REFERENCES Ingredient(ingredient_id),
                FOREIGN KEY (unit_id) REFERENCES Unit(unit_id),
                UNIQUE (quantity, ingredient_id, unit_id)
            )
        """)

    if 'Consumption' not in existing_tables:
        tables_to_create.append("""
            CREATE TABLE Consumption (
                consumption_id INTEGER PRIMARY KEY,
                consumption_date DATE NOT NULL DEFAULT (strftime('%d.%m.%Y', 'now')),
                ingredient_quantity_id INTEGER,
                ingredient_quantity_portions INTEGER DEFAULT 1,
                meal_type VARCHAR(20) DEFAULT 'other',
                FOREIGN KEY (ingredient_quantity_id) REFERENCES Ingredient_Quantity(ingredient_quantity_id),
                UNIQUE (consumption_date, ingredient_quantity_id, meal_type)
            )
        """)

    if 'Recipe' not in existing_tables:
        tables_to_create.append("""
            CREATE TABLE Recipe (
                recipe_id INTEGER PRIMARY KEY,
                recipe_name VARCHAR(255) NOT NULL UNIQUE,
                recipe_date DATE NOT NULL,
                servings TINYINT NOT NULL
            )
        """)

    if 'Recipe_Ingredients' not in existing_tables:
        tables_to_create.append("""
            CREATE TABLE Recipe_Ingredients (
                recipe_id INTEGER,
                ingredient_quantity_id INTEGER,
                FOREIGN KEY (recipe_id) REFERENCES Recipe(recipe_id) ON DELETE CASCADE,
                FOREIGN KEY (ingredient_quantity_id) REFERENCES Ingredient_Quantity(ingredient_quantity_id),
                PRIMARY KEY (recipe_id, ingredient_quantity_id)
            )
        """)

    if 'recipe_consumption' not in existing_tables:
        tables_to_create.append("""
            CREATE TABLE recipe_consumption (
                recipe_consumption_id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                consumption_date TEXT NOT NULL,
                meal_type TEXT DEFAULT 'other',
                servings REAL DEFAULT 1,
                FOREIGN KEY (recipe_id) REFERENCES Recipe(recipe_id) ON DELETE CASCADE,
                UNIQUE(recipe_id, consumption_date, meal_type)
            )
        """)

    if 'calorie_tracking' not in existing_tables:
        tables_to_create.append("""
            CREATE TABLE calorie_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                calories INTEGER NOT NULL,
                total_calories INTEGER
            )
        """)

    if 'body_weight_tracking' not in existing_tables:
        tables_to_create.append("""
            CREATE TABLE body_weight_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                weight REAL NOT NULL
            )
        """)

    if 'Favorites' not in existing_tables:
        tables_to_create.append("""
            CREATE TABLE Favorites (
                favorite_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ingredient_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ingredient_id) REFERENCES Ingredient(ingredient_id),
                UNIQUE(ingredient_id)
            )
        """)

    # Gym tracker tables
    if 'exercises' not in existing_tables:
        tables_to_create.append("""
            CREATE TABLE exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                muscle_group TEXT
            )
        """)

    if 'workout_sessions' not in existing_tables:
        tables_to_create.append("""
            CREATE TABLE workout_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                date DATE NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    if 'workout_sets' not in existing_tables:
        tables_to_create.append("""
            CREATE TABLE workout_sets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                exercise_id INTEGER NOT NULL,
                set_number INTEGER NOT NULL,
                weight REAL,
                reps INTEGER,
                FOREIGN KEY (session_id) REFERENCES workout_sessions(id) ON DELETE CASCADE,
                FOREIGN KEY (exercise_id) REFERENCES exercises(id)
            )
        """)

    # Execute table creation
    for create_statement in tables_to_create:
        cursor.execute(create_statement)
        print(f"Created table from: {create_statement.strip()[:50]}...")

    # Create indexes for better performance
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_consumption_date ON Consumption(consumption_date)",
        "CREATE INDEX IF NOT EXISTS idx_consumption_meal_type ON Consumption(meal_type)",
        "CREATE INDEX IF NOT EXISTS idx_recipe_consumption_date ON recipe_consumption(consumption_date)",
        "CREATE INDEX IF NOT EXISTS idx_workout_sessions_user_date ON workout_sessions(user_id, date)",
        "CREATE INDEX IF NOT EXISTS idx_workout_sets_session ON workout_sets(session_id)"
    ]

    for index in indexes:
        cursor.execute(index)

    conn.commit()
    conn.close()

    if tables_to_create:
        print(f"Database initialization complete. Created {len(tables_to_create)} tables.")
    else:
        print("All tables already exist. Database is ready.")

if __name__ == "__main__":
    init_database()
