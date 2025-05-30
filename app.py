from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import pandas as pd
import numpy as np
import os
from models.food import FoodDatabase
from models.foods.food_blueprint import food_blueprint
from models.nutrition_app.routes import nutrition_app
from models.calorie_weight import CalorieWeight
from datetime import datetime

app = Flask(__name__)

# Use environment variable for secret key, fallback to default for development
app.secret_key = os.getenv('SECRET_KEY', 'secret')

# Configure debug mode based on environment
app.config['DEBUG'] = os.getenv('DEBUG', 'False').lower() == 'true'

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Simple User class
class User(UserMixin):
    def __init__(self, id):
        self.id = id

# Hardcoded user credentials
USERS = {
    'plamenyankov': 'somestrongpassword'
}

@login_manager.user_loader
def load_user(user_id):
    if user_id in USERS:
        return User(user_id)
    return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username in USERS and USERS[username] == password:
            user = User(username)
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

app.register_blueprint(food_blueprint)
app.register_blueprint(nutrition_app)
food_db = FoodDatabase()
calorie_weight =CalorieWeight()

def transform_date_format(date_str):
    # Parse the input date string to a datetime object
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    # Format the datetime object to the desired string format
    return date_obj.strftime("%d.%m.%Y")

@app.route('/', methods=["GET", "POST"])
@login_required
def home():
    consumption = food_db.fetch_all_consumption()
    calories = calorie_weight.fetch_calories()
    weights = calorie_weight.fetch_weights()
    avg_consumed = food_db.get_avg_nutrition_consumed()
    if len(consumption) > 0:
        df = pd.DataFrame(consumption)
        df[['protein','carb']] = df[['protein','carb']] * 4
        df['fat'] = df['fat'] * 9
        # Convert 'date' column to datetime format
        df['date'] = pd.to_datetime(df['date'], format='%d.%m.%Y')
        df = df.sort_values(by='date', ascending=True)
        # Group by date and sum up the necessary columns
        grouped_data = df.groupby('date').agg({
            'protein': 'sum',
            'fat': 'sum',
            'carb': 'sum',
            'kcal':'sum'
        }).reset_index()

        dates = grouped_data['date'].tolist()
        proteins = grouped_data['protein'].tolist()
        fats = grouped_data['fat'].tolist()
        carbs = grouped_data['carb'].tolist()

    if len(calories) > 0:
        df_calories = pd.DataFrame(calories).reset_index()
        df_calories['date'] = pd.to_datetime(df_calories['date'], format='%d.%m.%Y')
        df_calories = df_calories.sort_values(by='date', ascending=True)
        date_calories = df_calories['date'].to_list()
        data_calories = df_calories['calories'].to_list()

        df_weight = pd.DataFrame(weights).reset_index()
        df_weight['date'] = pd.to_datetime(df_weight['date'], format='%d.%m.%Y')
        df_weight = df_weight.sort_values(by='date', ascending=True)
        date_weight = df_weight['date'].to_list()[1:]
        data_weight = df_weight['weight'].to_list()[1:]
        average_weight = np.round(np.mean(data_weight),1)


    return render_template('index.html',average_weight=average_weight,avg_consumed=avg_consumed,date_calories=date_calories,data_calories=data_calories, date_weight=date_weight,data_weight=data_weight, dates=dates, kcals=data_calories, proteins=proteins, fats=fats, carbs=carbs)


@app.route('/add_data', methods=["GET", "POST"])
@login_required
def add_data():
    date = datetime.now().strftime('%d.%m.%Y')

    if 'date' in request.form:
        date = transform_date_format(request.form['date'])

    if 'calories' in request.form:
        calories = request.form['calories']
        calorie_weight.add_calorie(date, calories)
    elif 'weight' in request.form:
        weight = request.form['weight']
        calorie_weight.add_weight(date, weight)


    calories = calorie_weight.fetch_calories()
    weights = calorie_weight.fetch_weights()
    return render_template('add_data.html', calories=calories, weights=weights)


if __name__ == "__main__":
    # Get debug mode from environment, default to True for development
    debug_mode = os.getenv('DEBUG', 'True').lower() == 'true'

    # Enable debug mode for development
    app.run(
        debug=debug_mode,
        host='127.0.0.1',  # Localhost
        port=5000,         # Default Flask port
        use_reloader=True, # Auto-reload on file changes
        use_debugger=True  # Enable interactive debugger
    )
