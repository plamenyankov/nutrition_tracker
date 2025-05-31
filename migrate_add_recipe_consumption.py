import sqlite3

def migrate():
    """Add recipe_consumption table to track recipes as single meal items"""
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    try:
        # Create recipe_consumption table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recipe_consumption (
                recipe_consumption_id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                consumption_date TEXT NOT NULL,
                meal_type TEXT DEFAULT 'other',
                servings REAL DEFAULT 1,
                FOREIGN KEY (recipe_id) REFERENCES Recipe(recipe_id) ON DELETE CASCADE,
                UNIQUE(recipe_id, consumption_date, meal_type)
            )
        """)

        conn.commit()
        print("Successfully created recipe_consumption table")

    except sqlite3.Error as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
