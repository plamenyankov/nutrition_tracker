import sqlite3

# Connect to the database
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

try:
    # Create Favorites table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Favorites (
            favorite_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ingredient_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ingredient_id) REFERENCES Ingredient(ingredient_id),
            UNIQUE(ingredient_id)
        )
    ''')
    print("Created Favorites table")

    conn.commit()
    print("Migration completed successfully!")

except sqlite3.Error as e:
    print(f"Error during migration: {e}")
    conn.rollback()

finally:
    conn.close()
