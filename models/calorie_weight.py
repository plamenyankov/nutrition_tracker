import sqlite3

DATABASE_PATH = 'sqlite:///../database.db'


class CalorieWeight:
    def __init__(self):
        self.conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)

    def close(self):
        if self.conn:
            self.conn.close()

    def add_calorie(self, date, calorie):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute('INSERT OR IGNORE INTO calorie_tracking (date, calories) VALUES (?,?)', (date, calorie,))

    def add_weight(self, date, weight):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute('INSERT OR IGNORE INTO body_weight_tracking (date, weight) VALUES (?,?)', (date,weight,))

    def fetch_weights(self):
        with self.conn:
            cursor = self.conn.cursor()
            weight = cursor.execute('SELECT * FROM body_weight_tracking ORDER BY date ASC').fetchall()

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
            calories = cursor.execute('SELECT * FROM calorie_tracking ORDER BY date ASC').fetchall()
            calories_data = []
            for c in calories:
                calories_data.append({
                    "date": c[0],
                    "calories": c[1]
                })
            print("fetch ", calories_data)

            return calories_data

