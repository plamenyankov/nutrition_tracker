from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import pandas as pd
import numpy as np
import os
from dotenv import load_dotenv
from flasgger import Swagger
from config.swagger_config import swagger_config, swagger_template
from models.food import FoodDatabase
from models.foods.food_blueprint import food_blueprint
# from models.nutrition_app.routes import nutrition_app  # Commented out - replaced by new blueprints
from models.blueprints.food_bp import food_bp
from models.blueprints.meal_bp import meal_bp
from models.blueprints.recipe_bp import recipe_bp
from models.blueprints.ai_bp import ai_bp
from models.blueprints.analytics_bp import analytics_bp
from models.blueprints.gym import gym_bp
from routes.timer_routes import timer_bp
from models.calorie_weight import CalorieWeight
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Use environment variable for secret key, fallback to default for development
app.secret_key = os.getenv('SECRET_KEY', 'secret')

# Initialize Swagger UI
swagger = Swagger(app, config=swagger_config, template=swagger_template)

# Configure debug mode based on environment
app.config['DEBUG'] = os.getenv('DEBUG', 'False').lower() == 'true'

# Configure file upload limits
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max file size

# Configure session
app.config['SESSION_PERMANENT'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour session lifetime

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
    'plamenyankov': 'somestrongpassword',
    'demo': 'demo'
}

@login_manager.user_loader
def load_user(user_id):
    if user_id in USERS:
        return User(user_id)
    return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    User login endpoint
    ---
    tags:
      - Authentication
    parameters:
      - name: username
        in: formData
        type: string
        required: true
        description: Username
      - name: password
        in: formData
        type: string
        required: true
        description: Password
    responses:
      302:
        description: Redirect to home page on success
      200:
        description: Login page with error message
    """
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
    else:
        # Clear any existing flash messages when showing login page (GET request)
        # This prevents messages from other pages showing up on login
        from flask import session
        session.pop('_flashes', None)

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Register old blueprint (to be removed later)
app.register_blueprint(food_blueprint)
# app.register_blueprint(nutrition_app)  # Commented out - replaced by new blueprints

# Register new modular blueprints
app.register_blueprint(food_bp)
app.register_blueprint(meal_bp)
app.register_blueprint(recipe_bp)
app.register_blueprint(ai_bp)
app.register_blueprint(analytics_bp)
app.register_blueprint(gym_bp)
app.register_blueprint(timer_bp)

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
    """
    Home dashboard with nutrition overview
    ---
    tags:
      - Dashboard
    security:
      - LoginRequired: []
    responses:
      200:
        description: Home dashboard page
        schema:
          type: object
          properties:
            status:
              type: string
              example: "success"
    """
    consumption = food_db.fetch_all_consumption()
    calories = calorie_weight.fetch_calories()
    weights = calorie_weight.fetch_weights()
    avg_consumed = food_db.get_avg_nutrition_consumed()

    # Handle None values in avg_consumed
    if avg_consumed is None:
        avg_consumed = {
            "kcal": 0, "fat": 0, "carb": 0, "fiber": 0,
            "net_carb": 0, "protein": 0, "cnt": 0
        }
    else:
        # Ensure all values are not None
        for key in ["kcal", "fat", "carb", "fiber", "net_carb", "protein", "cnt"]:
            if avg_consumed.get(key) is None:
                avg_consumed[key] = 0

    # Initialize variables with defaults
    dates = []
    proteins = []
    fats = []
    carbs = []
    date_calories = []
    data_calories = []
    date_weight = []
    data_weight = []
    average_weight = 0

    if len(consumption) > 0:
        df = pd.DataFrame(consumption)
        df[['protein','carb']] = df[['protein','carb']] * 4
        df['fat'] = df['fat'] * 9

        # Convert 'date' column to datetime format - handle multiple formats
        # Try to parse dates without specifying format, let pandas infer
        try:
            # First try with pd.to_datetime without any format specification
            df['date'] = pd.to_datetime(df['date'])
        except:
            # If that fails, try with dayfirst=True for DD.MM.YYYY formats
            try:
                df['date'] = pd.to_datetime(df['date'], dayfirst=True)
            except:
                # As a last resort, try to parse each date individually
                df['date'] = df['date'].apply(lambda x: pd.to_datetime(x, errors='coerce'))

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
        # Handle multiple date formats for calories
        try:
            df_calories['date'] = pd.to_datetime(df_calories['date'])
        except:
            try:
                df_calories['date'] = pd.to_datetime(df_calories['date'], dayfirst=True)
            except:
                df_calories['date'] = df_calories['date'].apply(lambda x: pd.to_datetime(x, errors='coerce'))

        df_calories = df_calories.sort_values(by='date', ascending=True)
        date_calories = df_calories['date'].to_list()
        data_calories = df_calories['calories'].to_list()

    if len(weights) > 0:
        df_weight = pd.DataFrame(weights).reset_index()
        # Handle multiple date formats for weights
        try:
            df_weight['date'] = pd.to_datetime(df_weight['date'])
        except:
            try:
                df_weight['date'] = pd.to_datetime(df_weight['date'], dayfirst=True)
            except:
                df_weight['date'] = df_weight['date'].apply(lambda x: pd.to_datetime(x, errors='coerce'))

        df_weight = df_weight.sort_values(by='date', ascending=True)
        date_weight = df_weight['date'].to_list()[1:] if len(df_weight) > 1 else []
        data_weight = df_weight['weight'].to_list()[1:] if len(df_weight) > 1 else []
        average_weight = np.round(np.mean(data_weight),1) if len(data_weight) > 0 else 0


    return render_template('index.html',average_weight=average_weight,avg_consumed=avg_consumed,date_calories=date_calories,data_calories=data_calories, date_weight=date_weight,data_weight=data_weight, dates=dates, kcals=data_calories, proteins=proteins, fats=fats, carbs=carbs)


@app.route('/add_data', methods=["GET", "POST"])
@login_required
def add_data():
    date = datetime.now().strftime('%d.%m.%Y')

    if 'date' in request.form:
        date = transform_date_format(request.form['date'])

    if 'calories' in request.form:
        active_calories = request.form['calories']
        total_calories = request.form.get('total_calories', None)
        # Convert empty string to None
        if total_calories == '':
            total_calories = None
        calorie_weight.add_calorie(date, active_calories, total_calories)
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
    port = int(os.getenv('FLASK_RUN_PORT', 8080))  # Use port 8080 to avoid AirPlay conflict
    app.run(
        debug=debug_mode,
        host='127.0.0.1',  # Localhost
        port=port,
        use_reloader=True, # Auto-reload on file changes
        use_debugger=True  # Enable interactive debugger
    )
