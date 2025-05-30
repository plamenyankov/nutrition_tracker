import sqlite3

# Connect to the database
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

try:
    # Check if meal_type column already exists
    cursor.execute("PRAGMA table_info(Consumption)")
    columns = [column[1] for column in cursor.fetchall()]

    if 'meal_type' not in columns:
        # Add meal_type column to Consumption table
        cursor.execute('''
            ALTER TABLE Consumption
            ADD COLUMN meal_type VARCHAR(20) DEFAULT 'other'
        ''')
        print("Added meal_type column to Consumption table")

        # Update existing records with a default meal type based on time
        # This is optional - you can remove if you want all existing to be 'other'
        cursor.execute('''
            UPDATE Consumption
            SET meal_type = 'other'
            WHERE meal_type IS NULL
        ''')
        print("Updated existing records with default meal type")

        conn.commit()
        print("Migration completed successfully!")
    else:
        print("meal_type column already exists, skipping migration")

except sqlite3.Error as e:
    print(f"Error during migration: {e}")
    conn.rollback()

finally:
    conn.close()
