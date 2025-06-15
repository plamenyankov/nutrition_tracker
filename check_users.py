#!/usr/bin/env python3
import os
from dotenv import load_dotenv
load_dotenv('.env')

from models.database.connection_manager import get_db_manager

# Check development database
os.environ['FLASK_ENV'] = 'development'
db = get_db_manager(use_mysql=True)
with db.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users')
    users = cursor.fetchall()
    print('Users in development database:')
    for user in users:
        print(f'  ID: {user[0]}, Username: {user[1]}')
