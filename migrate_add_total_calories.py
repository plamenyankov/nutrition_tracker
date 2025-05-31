import sqlite3

def migrate():
    """Add total_calories column to calorie_tracking table"""
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    try:
        # Check if the column already exists
        cursor.execute("PRAGMA table_info(calorie_tracking)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'total_calories' not in columns:
            # Add the total_calories column
            cursor.execute("""
                ALTER TABLE calorie_tracking
                ADD COLUMN total_calories INTEGER
            """)
            conn.commit()
            print("Successfully added total_calories column to calorie_tracking table")
        else:
            print("total_calories column already exists")

    except sqlite3.Error as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
