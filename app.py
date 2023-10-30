from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import pandas as pd
from models.food import FoodDatabase
from models.foods.food_blueprint import food_blueprint


app = Flask(__name__)
app.secret_key = 'secret'  # This is for flash messaging
app.register_blueprint(food_blueprint)
food_db = FoodDatabase()


@app.route('/', methods=["GET", "POST"])
def home():

    consumption = food_db.fetch_all_consumption()
    if len(consumption) > 0:
        df = pd.DataFrame(consumption)
        df[['protein','carb']] = df[['protein','carb']] * 4
        df['fat'] = df['fat'] * 9

        data = df.to_dict(orient='records')
        columns = df.columns

        # Create a bar chart
        # Group by date and sum up the necessary columns
        grouped_data = df.groupby('date').agg({
            'protein': 'sum',
            'fat': 'sum',
            'carb': 'sum',
            'kcal':'sum'
        }).reset_index()

        kcals = grouped_data['kcal'].tolist()
        dates = grouped_data['date'].tolist()
        proteins = grouped_data['protein'].tolist()
        fats = grouped_data['fat'].tolist()
        carbs = grouped_data['carb'].tolist()



    return render_template('index.html', data=data, columns=columns, dates=dates, kcals=kcals, proteins=proteins, fats=fats, carbs=carbs)



if __name__ == "__main__":
    app.run(debug=True)
