import os
import sqlite3

# Use environment variable for database path
db_path = os.getenv('DATABASE_PATH', 'database.db')
# Convert to absolute path if needed
if not db_path.startswith('/'):
    db_path = os.path.abspath(db_path)
DATABASE_PATH = db_path


class CalorieWeight:
    def __init__(self):
        self.conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)

    def close(self):
        if self.conn:
            self.conn.close()

    def add_calorie(self, date, active_calories, total_calories=None):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute('INSERT OR IGNORE INTO calorie_tracking (date, calories, total_calories) VALUES (?,?,?)',
                         (date, active_calories, total_calories))

    def add_weight(self, date, weight):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute('INSERT OR IGNORE INTO body_weight_tracking (date, weight) VALUES (?,?)', (date,weight,))

    def fetch_weights(self):
        with self.conn:
            cursor = self.conn.cursor()
            # Convert DD.MM.YYYY to YYYY-MM-DD for proper sorting
            weight = cursor.execute('''
                SELECT date, weight
                FROM body_weight_tracking
                ORDER BY
                    substr(date, 7, 4) || '-' ||
                    substr(date, 4, 2) || '-' ||
                    substr(date, 1, 2) DESC
            ''').fetchall()

            weight_data = []
            for w in weight:
                weight_data.append({
                    "date": w[0],
                    "weight": w[1]
                })

            return weight_data

    def fetch_calories(self):
        with self.conn:
            cursor = self.conn.cursor()
            # Convert DD.MM.YYYY to YYYY-MM-DD for proper sorting
            calories = cursor.execute('''
                SELECT date, calories, total_calories
                FROM calorie_tracking
                ORDER BY
                    substr(date, 7, 4) || '-' ||
                    substr(date, 4, 2) || '-' ||
                    substr(date, 1, 2) DESC
            ''').fetchall()
            calories_data = []
            for c in calories:
                calories_data.append({
                    "date": c[0],
                    "calories": c[1],  # active calories
                    "total_calories": c[2] if len(c) > 2 else None
                })
            print("fetch ", calories_data)

            return calories_data
