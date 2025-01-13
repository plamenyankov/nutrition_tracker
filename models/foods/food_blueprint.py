from flask import Blueprint
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from datetime import datetime
from models.food import FoodDatabase
import pandas as pd
import io
from models import openai_utils

food_blueprint = Blueprint('foods', __name__)
food_db = FoodDatabase()
temp_df = None

def transform_date_format(date_str):
    # Parse the input date string to a datetime object
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    # Format the datetime object to the desired string format
    return date_obj.strftime("%d.%m.%Y")

def add_foods_to_consumption(date, ingredient_quantity_ids):
    for ingredient_quantity_id in ingredient_quantity_ids:
        food_db.save_consumption(date, ingredient_quantity_id)

def get_ingredients_from_recipes(recipes_ids):
    ingredients_quantity_ids = None
    for recipes_id in recipes_ids:
        ingredients_quantity_ids = food_db.fetch_recipe_ingredients(recipes_id)
    return ingredients_quantity_ids

def save_ingredients():
    global temp_df
    temp_df.columns = temp_df.columns.str.strip()
    ingredient_quantity_ids = food_db.save_to_database(temp_df.to_csv(index=False))
    return ingredient_quantity_ids

def save_recipe(date, form):
    global temp_df
    serv = 1

    if form['recipe'] is None:
        return redirect(url_for('foods'))

    if form['serv'] is not None:
        serv = form['serv']

    recipe_name = form['recipe']
    temp_df.columns = temp_df.columns.str.strip()
    ingredient_quantity_ids = food_db.save_recipe(date, recipe_name, serv, temp_df.to_csv(index=False))

    return ingredient_quantity_ids


@food_blueprint.route('/nutrition/<int:nutrition_id>', methods=['GET','POST'])
def nutrition(nutrition_id):
    if 'action' in request.form:
        action = request.form['action']
        if action == "Edit Food":
            updated_nutrition = {
                "qty": request.form["qty"],
                "carb": request.form["carb"],
                "fat": request.form["fat"],
                "protein": request.form["protein"],
                "net_carb": request.form["net_carb"],
                "fiber": request.form["fiber"],
                "kcal": request.form["kcal"]
            }
            food_db.update_nutrition(nutrition_id, updated_nutrition)
        elif action == "Consume":
            if request.form['date'] != '':
                date = transform_date_format(request.form['date'])
            else:
                date = datetime.now().strftime('%d.%m.%Y')
            add_foods_to_consumption(date, [nutrition_id])

    nutrition = food_db.fetch_nutrition(nutrition_id)
    return render_template('nutrition.html', nutrition=nutrition)

@food_blueprint.route('/food', methods=['GET','POST'])
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
    all_consumption = pd.DataFrame(all_consumption)
    all_consumption['date'] = pd.to_datetime(all_consumption['date'], format='%d.%m.%Y')
    all_consumption = all_consumption.sort_values(by='date', ascending=False)
    all_consumption['date'] = all_consumption['date'].dt.strftime('%d.%m.%Y')
    all_consumption = all_consumption.to_dict(orient='records')
    # filtered_nutritions = all_nutritions['ingredient'].unique()
    # print(filtered_nutritions)
    # print(all_nutritions.sort_values(by='ingredient'))
    all_recipes = food_db.fetch_all_recipes()
    return render_template('food.html', data=data, columns=columns,  nutritions= all_nutritions, consumption=all_consumption, recipes=all_recipes)
@food_blueprint.route('/consume_food', methods=['POST'])
def consume_food():
    date = datetime.now().strftime('%d.%m.%Y')
    if 'date' in request.form and request.form['date'] != '':
        date = transform_date_format(request.form['date'])
    # Get IQ id & qty
    qty = request.form['qty']
    iq_id = request.form['iq_id']
    # Get ingredient & unit ids
    ingredient_id, unit_id = food_db.get_unit_ingredient_from_iq(iq_id)
    # Save new IQ with qty
    ingredient_quantity_id = food_db.save_ingredient_qty(qty, ingredient_id, unit_id)
    # save to consume
    food_db.save_consumption(date, ingredient_quantity_id)
    return redirect(url_for('foods.food'))

@food_blueprint.route('/recipe/<int:recipe_id>', methods=['GET','POST'])
def recipe(recipe_id):
    all_recipes = food_db.fetch_all_recipes()
    ingredients = None

    if 'recipe_page' in request.form:
        recipe_id = request.form['recipe_id']
        recipe_ingredients = get_ingredients_from_recipes(recipe_id)

    if recipe_id:
        recipe_ingredients = food_db.fetch_recipe_ingredients(recipe_id)
        ingredients = []
        for iq_id in recipe_ingredients:
            ingredients.append(food_db.fetch_nutrition(iq_id))

    return render_template('recipe.html', recipes=all_recipes, nutritions=ingredients)

@food_blueprint.route('/preview_openai_response', methods=['POST'])
def preview_openai_response():
    global temp_df
    user_input = request.form['foods']
    # Call OpenAI API here
    response = openai_utils.get_openai_response(user_input)
    # Convert the response to a DataFrame
    data_io = io.StringIO(response)
    temp_df = pd.read_csv(data_io)

    return redirect(url_for('foods.food'))

@food_blueprint.route('/handle_ingredients_action', methods=['POST'])
def handle_ingredients_action():
    action = request.form['action']
    # This will return a list of all the ingredient_ids from the checked checkboxes
    ingredient_ids = request.form.getlist('remove_ids[]')

    if action == "consume":
        date = datetime.now().strftime('%d.%m.%Y')
        add_foods_to_consumption(date, ingredient_ids)

    elif action == "delete":
        # Now you can iterate over this list and process each ID as needed
        for ingredient_id in ingredient_ids:
            # Your logic to delete or process the ingredient_id goes here
            food_db.delete_ingredient_qty(ingredient_id)

    return redirect(url_for('foods.food'))

@food_blueprint.route('/handle_recipe_action', methods=['POST'])
def handle_recipe_action():
     # This will return a list of all the ingredient_ids from the checked checkboxes
    recipe_ids = request.form.getlist('remove_ids[]')

    if len(recipe_ids) == 0:
        return redirect(url_for('foods.food'))

    action = request.form['action']
    ingredient_ids = get_ingredients_from_recipes(recipe_ids)
    date = datetime.now().strftime('%d.%m.%Y')

    if 'date' in request.form and request.form['date'] != '':
        date = transform_date_format(request.form['date'])


    if action == "Consume":
        add_foods_to_consumption(date, ingredient_ids)

    elif action == "Delete":
        # Now you can iterate over this list and process each ID as needed
        for ingredient_id in recipe_ids:
            # Your logic to delete recipe
            food_db.delete_recipe(ingredient_id)
    # elif action == 'Edit':
    #     return

    return redirect(url_for('foods.food'))

@food_blueprint.route('/remove_consumption', methods=['POST'])
def remove_consumption():
    # This will return a list of all the ingredient_ids from the checked checkboxes
    ingredient_ids_to_remove = request.form.getlist('remove_ids[]')

    # Now you can iterate over this list and process each ID as needed
    for ingredient_id in ingredient_ids_to_remove:
        # Your logic to delete or process the ingredient_id goes here
        food_db.delete_consumption(ingredient_id)

    return redirect(url_for('foods.food'))


@food_blueprint.route('/handle_food_actions', methods=['POST'])
def handle_food_actions():
    global temp_df
    button_clicked = request.form['action']

    date = datetime.now().strftime('%d.%m.%Y')

    if 'date' in request.form and request.form['date'] != '':
        date = transform_date_format(request.form['date'])

    if button_clicked == "Save Ingredients":
        ingredient_quantity_ids = save_ingredients()

    elif button_clicked == "Save as Recipe":
        ingredient_quantity_ids = save_recipe(date, request.form)

    elif button_clicked == "Save Food":
        ingredient_obj = {
            "qty":request.form["qty"],
            "unit":request.form["unit"],
            "ingr":request.form["ingredient"],
            "carbs":request.form["carb"],
            "fats":request.form["fat"],
            "protein":request.form["protein"],
            "net_carbs":request.form["net_carb"],
            "fiber":request.form["fiber"],
            "kcal":request.form["kcal"]
        }
        temp_df = pd.DataFrame([ingredient_obj])
        ingredient_quantity_ids = save_ingredients()

    else:
        temp_df = None
        return redirect(url_for('foods.food'))

    if 'consumption' in request.form:
        add_foods_to_consumption(date, ingredient_quantity_ids)

    temp_df = None

    return redirect(url_for('foods.food'))

