from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import pandas as pd
from datetime import datetime
import io
import sqlite3
from models import openai_utils
# from models.food import save_to_database, fetch_all_nutritions
from models.food import FoodDatabase





app = Flask(__name__)
app.secret_key = 'secret'  # This is for flash messaging
temp_df = None
food_db = FoodDatabase()
@app.route('/ingr')
def get_unit():
    unit_id = food_db.save_ingredient('chicken')
    return jsonify(unit_id)

@app.route('/nutrition', methods=['GET'])
def get_nutrition():
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM nutrition')
        results = cursor.fetchall()
    return jsonify(results)
@app.route('/', methods=["GET", "POST"])
def home():

    df = pd.read_csv('data/data.csv')
    df2 = pd.read_csv('data/iwatch.csv')
    data = df.to_dict(orient='records')
    columns = df.columns

    # Create a bar chart
    # Group by date and sum up the necessary columns
    grouped_data = df.groupby('date').agg({
        'protein': 'sum',
        'fats': 'sum',
        'carbs': 'sum'
    }).reset_index()
    kcals = df2.groupby('date')['kcal'].sum().tolist()
    dates = grouped_data['date'].tolist()
    proteins = grouped_data['protein'].tolist()
    fats = grouped_data['fats'].tolist()
    carbs = grouped_data['carbs'].tolist()

    return render_template('input_form.html', data=data, columns=columns, dates=dates, kcals=kcals, proteins=proteins, fats=fats, carbs=carbs)

@app.route('/food', methods=['GET','POST'])
def food():
    global temp_df
    data = None
    columns = None
    if temp_df is not None:
        current_date = datetime.now().strftime('%d.%m.%Y')
        temp_df['date'] = current_date
        data = temp_df.to_dict(orient='records')
        columns = temp_df.columns
    all_nutritions = food_db.fetch_all_nutrition()
    all_consumption = food_db.fetch_all_consumption()
    return render_template('food.html', data=data, columns=columns,  nutritions= all_nutritions, consumption=all_consumption)
@app.route('/preview', methods=["GET", "POST"])
def preview():
    global temp_df
    data = None
    columns = None
    if temp_df is not None:
        current_date = datetime.now().strftime('%d.%m.%Y')
        temp_df['date'] = current_date
        data = temp_df.to_dict(orient='records')
        columns = temp_df.columns
    return render_template('preview.html', data=data, columns=columns)
@app.route('/submit', methods=['POST'])
def submit():
    global temp_df

    user_input = request.form['foods']

    # Call OpenAI API here
    response = openai_utils.get_openai_response(user_input)

    print('Response', response)
    # Convert the response to a DataFrame
    data_io = io.StringIO(response)
    temp_df = pd.read_csv(data_io)

    return redirect(url_for('food'))

@app.route('/remove_ingredient', methods=['POST'])
def remove_ingredient():
    # This will return a list of all the ingredient_ids from the checked checkboxes
    ingredient_ids_to_remove = request.form.getlist('remove_ids[]')

    # Now you can iterate over this list and process each ID as needed
    for ingredient_id in ingredient_ids_to_remove:
        # Your logic to delete or process the ingredient_id goes here
        food_db.delete_ingredient(ingredient_id)

    return redirect(url_for('food'))

@app.route('/remove_consumption', methods=['POST'])
def remove_consumption():
    # This will return a list of all the ingredient_ids from the checked checkboxes
    ingredient_ids_to_remove = request.form.getlist('remove_ids[]')

    # Now you can iterate over this list and process each ID as needed
    for ingredient_id in ingredient_ids_to_remove:
        # Your logic to delete or process the ingredient_id goes here
        food_db.delete_consumption(ingredient_id)

    return redirect(url_for('food'))


def save_ingredients(date, form):
    global temp_df

    temp_df.columns = temp_df.columns.str.strip()

    ingredient_quantity_ids = food_db.save_to_database(temp_df.to_csv(index=False))
    return ingredient_quantity_ids
def save_recipe(date, form):
    global temp_df
    serv = 1

    if form['recipe'] is None:
        return redirect(url_for('food'))
    if form['serv'] is not None:
        serv = form['serv']

    recipe = form['recipe']

    temp_df.columns = temp_df.columns.str.strip()

    ingredient_quantity_ids = food_db.save_recipe(date, recipe, serv, temp_df.to_csv(index=False))
    return ingredient_quantity_ids
@app.route('/save_food', methods=['POST'])
def save_food():
    global temp_df
    button_clicked = request.form['action']
    ingredient_quantity_ids = []
    date = datetime.now().strftime('%d.%m.%Y')
    if request.form['date'] is None:
        date = request.form['date']

    if button_clicked == "Save Ingredients":
        ingredient_quantity_ids = save_ingredients(date, request.form)
    elif button_clicked == "Save as Recipe":
        ingredient_quantity_ids = save_recipe(date, request.form)
    else:
        # Logic for cancel, e.g., redirect to another page
        temp_df = None
        return redirect(url_for('food'))

    if request.form['consumption'] is not None:
        for ingredient_quantity_id in ingredient_quantity_ids:
            food_db.save_consumption(date, ingredient_quantity_id)
    temp_df = None
    return redirect(url_for('food'))



@app.route('/chart')
def chart():
    # Load data from CSV
    df = pd.read_csv('data/data.csv')

    # Data processing for chart (group by date, summarize, etc.) goes here

    # Render chart - you can use a library like Plotly or Matplotlib to generate and show charts
    return "Chart goes here!"


if __name__ == "__main__":
    app.run(debug=True)
