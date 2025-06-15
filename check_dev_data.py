#!/usr/bin/env python3
import os
from dotenv import load_dotenv
load_dotenv('.env')

from models.database.connection_manager import get_db_manager

# Force development environment
os.environ['FLASK_ENV'] = 'development'
db = get_db_manager(use_mysql=True)
with db.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute('SELECT DATABASE()')
    print('Connected to:', cursor.fetchone()[0])

    tables = ['exercises', 'users', 'workout_sessions', 'workout_sets', 'Unit', 'Consumption', 'Ingredient', 'Recipe']
    for table in tables:
        try:
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            count = cursor.fetchone()[0]
            print(f'{table}: {count} rows')
        except Exception as e:
            print(f'{table}: Error - {e}')
