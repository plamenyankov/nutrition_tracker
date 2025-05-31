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
                ingredient_name TEXT PRIMARY KEY,
                density REAL,
                serving TEXT
            )
        """)

    if 'Unit' not in existing_tables:
        tables_to_create.append("""
            CREATE TABLE Unit (
                unit_name TEXT PRIMARY KEY,
                short_name TEXT
            )
        """)

    if 'Nutrition' not in existing_tables:
        tables_to_create.append("""
            CREATE TABLE Nutrition (
                ingredient_name TEXT PRIMARY KEY,
                protein REAL,
                carb REAL,
                fat REAL,
                kcal REAL,
                FOREIGN KEY (ingredient_name) REFERENCES Ingredient(ingredient_name)
            )
        """)

    if 'Ingredient_Quantity' not in existing_tables:
        tables_to_create.append("""
            CREATE TABLE Ingredient_Quantity (
                ingredient_name TEXT,
                quantity REAL,
                unit TEXT,
                PRIMARY KEY (ingredient_name, quantity, unit),
                FOREIGN KEY (ingredient_name) REFERENCES Ingredient(ingredient_name),
                FOREIGN KEY (unit) REFERENCES Unit(unit_name)
            )
        """)

    if 'Consumption' not in existing_tables:
        tables_to_create.append("""
            CREATE TABLE Consumption (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ingredient_name TEXT,
                quantity REAL,
                unit TEXT,
                protein REAL,
                carb REAL,
                fat REAL,
                kcal REAL,
                date TEXT,
                meal_type TEXT DEFAULT 'meal',
                FOREIGN KEY (ingredient_name) REFERENCES Ingredient(ingredient_name),
                FOREIGN KEY (unit) REFERENCES Unit(unit_name)
            )
        """)

    if 'Recipe' not in existing_tables:
        tables_to_create.append("""
            CREATE TABLE Recipe (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                instructions TEXT,
                prep_time INTEGER,
                cook_time INTEGER,
                servings INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    if 'Recipe_Ingredients' not in existing_tables:
        tables_to_create.append("""
            CREATE TABLE Recipe_Ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                ingredient_name TEXT NOT NULL,
                quantity REAL NOT NULL,
                unit TEXT NOT NULL,
                FOREIGN KEY (recipe_id) REFERENCES Recipe(id) ON DELETE CASCADE,
                FOREIGN KEY (ingredient_name) REFERENCES Ingredient(ingredient_name),
                FOREIGN KEY (unit) REFERENCES Unit(unit_name)
            )
        """)

    if 'recipe_consumption' not in existing_tables:
        tables_to_create.append("""
            CREATE TABLE recipe_consumption (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                recipe_name TEXT NOT NULL,
                servings_consumed REAL NOT NULL DEFAULT 1,
                date TEXT NOT NULL,
                meal_type TEXT DEFAULT 'meal',
                FOREIGN KEY (recipe_id) REFERENCES Recipe(id)
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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ingredient_name TEXT NOT NULL,
                quantity REAL NOT NULL,
                unit TEXT NOT NULL,
                UNIQUE(ingredient_name, quantity, unit),
                FOREIGN KEY (ingredient_name) REFERENCES Ingredient(ingredient_name),
                FOREIGN KEY (unit) REFERENCES Unit(unit_name)
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
        "CREATE INDEX IF NOT EXISTS idx_consumption_date ON Consumption(date)",
        "CREATE INDEX IF NOT EXISTS idx_consumption_meal_type ON Consumption(meal_type)",
        "CREATE INDEX IF NOT EXISTS idx_recipe_consumption_date ON recipe_consumption(date)",
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
