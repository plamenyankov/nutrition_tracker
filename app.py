from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import pandas as pd
from models.food import FoodDatabase
from models.foods.food_blueprint import food_blueprint
from models.calorie_weight import CalorieWeight
from datetime import datetime
app = Flask(__name__)
app.secret_key = 'secret'  # This is for flash messaging
app.register_blueprint(food_blueprint)
food_db = FoodDatabase()
calorie_weight =CalorieWeight()

def transform_date_format(date_str):
    # Parse the input date string to a datetime object
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    # Format the datetime object to the desired string format
    return date_obj.strftime("%d.%m.%Y")

@app.route('/', methods=["GET", "POST"])
def home():
    consumption = food_db.fetch_all_consumption()
    calories = calorie_weight.fetch_calories()
    weights = calorie_weight.fetch_weights()
    if len(consumption) > 0:
        df = pd.DataFrame(consumption)
        df[['protein','carb']] = df[['protein','carb']] * 4
        df['fat'] = df['fat'] * 9

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
        print(dates)
        print(fats)
    if len(calories) > 0:
        df_calories = pd.DataFrame(calories).reset_index()
        date_calories = df_calories['date'].to_list()
        data_calories = df_calories['calories'].to_list()

        df_weight = pd.DataFrame(weights).reset_index()
        date_weight = df_weight['date'].to_list()
        data_weight = df_weight['weight'].to_list()

    return render_template('index.html',date_calories=date_calories,data_calories=data_calories, date_weight=date_weight,data_weight=data_weight, dates=dates, kcals=data_calories, proteins=proteins, fats=fats, carbs=carbs)


@app.route('/add_data', methods=["GET", "POST"])
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
    app.run(debug=True)
