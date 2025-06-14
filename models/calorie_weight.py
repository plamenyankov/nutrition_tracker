import os
from models.database.connection_manager import DatabaseConnectionManager

# Use environment variable for database path (for backward compatibility)
db_path = os.getenv('DATABASE_PATH', 'database.db')
# Convert to absolute path if needed
if not db_path.startswith('/'):
    db_path = os.path.abspath(db_path)
DATABASE_PATH = db_path


class CalorieWeight:
    def __init__(self):
        self.connection_manager = DatabaseConnectionManager(use_mysql=True)

    def close(self):
        # DatabaseConnectionManager doesn't need explicit closing
        pass

    def add_calorie(self, date, active_calories, total_calories=None):
        with self.connection_manager.get_connection() as conn:
            cursor = conn.cursor()
            if self.connection_manager.use_mysql:
                cursor.execute('INSERT IGNORE INTO calorie_tracking (date, calories, total_calories) VALUES (%s,%s,%s)',
                             (date, active_calories, total_calories))
            else:
                cursor.execute('INSERT OR IGNORE INTO calorie_tracking (date, calories, total_calories) VALUES (?,?,?)',
                             (date, active_calories, total_calories))

    def add_weight(self, date, weight):
        with self.connection_manager.get_connection() as conn:
            cursor = conn.cursor()
            if self.connection_manager.use_mysql:
                cursor.execute('INSERT IGNORE INTO body_weight_tracking (date, weight) VALUES (%s,%s)', (date, weight))
            else:
                cursor.execute('INSERT OR IGNORE INTO body_weight_tracking (date, weight) VALUES (?,?)', (date, weight))

    def fetch_weights(self):
        with self.connection_manager.get_connection() as conn:
            cursor = conn.cursor()
            if self.connection_manager.use_mysql:
                # MySQL version - handle date sorting differently
                query = '''
                    SELECT date, weight
                    FROM body_weight_tracking
                    ORDER BY STR_TO_DATE(date, '%d.%m.%Y') DESC
                '''
            else:
                # SQLite version - Convert DD.MM.YYYY to YYYY-MM-DD for proper sorting
                query = '''
                    SELECT date, weight
                    FROM body_weight_tracking
                    ORDER BY
                        substr(date, 7, 4) || '-' ||
                        substr(date, 4, 2) || '-' ||
                        substr(date, 1, 2) DESC
                '''
            cursor.execute(query)
            weight = cursor.fetchall()

            weight_data = []
            for w in weight:
                weight_data.append({
                    "date": w[0],
                    "weight": w[1]
                })

            return weight_data

    def fetch_calories(self):
        with self.connection_manager.get_connection() as conn:
            cursor = conn.cursor()
            if self.connection_manager.use_mysql:
                # MySQL version - handle date sorting differently
                query = '''
                    SELECT date, calories, total_calories
                    FROM calorie_tracking
                    ORDER BY STR_TO_DATE(date, '%d.%m.%Y') DESC
                '''
            else:
                # SQLite version - Convert DD.MM.YYYY to YYYY-MM-DD for proper sorting
                query = '''
                    SELECT date, calories, total_calories
                    FROM calorie_tracking
                    ORDER BY
                        substr(date, 7, 4) || '-' ||
                        substr(date, 4, 2) || '-' ||
                        substr(date, 1, 2) DESC
                '''
            cursor.execute(query)
            calories = cursor.fetchall()
            calories_data = []
            for c in calories:
                calories_data.append({
                    "date": c[0],
                    "calories": c[1],  # active calories
                    "total_calories": c[2] if len(c) > 2 else None
                })
            print("fetch ", calories_data)

            return calories_data
