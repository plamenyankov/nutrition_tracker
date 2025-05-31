from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from models.food import FoodDatabase
from models.calorie_weight import CalorieWeight

analytics_bp = Blueprint('analytics_bp', __name__, url_prefix='/analytics')

food_db = FoodDatabase()
calorie_weight = CalorieWeight()

@analytics_bp.route('')
@login_required
def analytics():
    """Analytics - View nutrition trends and insights"""
    # Get date range (default: last 30 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    # Fetch consumption data
    consumption = food_db.fetch_all_consumption()
    calories_data = calorie_weight.fetch_calories()
    weights_data = calorie_weight.fetch_weights()

    # Process data for initial display
    summary_stats = calculate_summary_stats(consumption, start_date, end_date)

    return render_template('nutrition_app/analytics.html',
                         summary_stats=summary_stats,
                         start_date=start_date.strftime('%Y-%m-%d'),
                         end_date=end_date.strftime('%Y-%m-%d'))

@analytics_bp.route('/data')
@login_required
def get_analytics_data():
    """API endpoint to fetch analytics data for charts"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    else:
        start_date = datetime.now() - timedelta(days=30)

    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        end_date = datetime.now()

    # Fetch all data
    consumption = food_db.fetch_all_consumption()
    calories_data = calorie_weight.fetch_calories()
    weights_data = calorie_weight.fetch_weights()

    # Process data
    daily_nutrition = process_daily_nutrition(consumption, start_date, end_date)
    weight_trend = process_weight_trend(weights_data, start_date, end_date)
    calorie_trend = process_calorie_trend(calories_data, start_date, end_date)
    macro_distribution = calculate_macro_distribution(consumption, start_date, end_date)
    food_frequency = calculate_food_frequency(consumption, start_date, end_date)
    weekly_averages = calculate_weekly_averages(consumption, start_date, end_date)

    return jsonify({
        'daily_nutrition': daily_nutrition,
        'weight_trend': weight_trend,
        'calorie_trend': calorie_trend,
        'macro_distribution': macro_distribution,
        'food_frequency': food_frequency,
        'weekly_averages': weekly_averages
    })

def calculate_summary_stats(consumption, start_date, end_date):
    """Calculate summary statistics for the given date range"""
    if not consumption:
        return {
            'avg_calories': 0,
            'avg_protein': 0,
            'avg_carbs': 0,
            'avg_fat': 0,
            'total_days': 0,
            'total_meals': 0
        }

    df = pd.DataFrame(consumption)
    # Convert date strings to datetime (DD.MM.YYYY format)
    df['date'] = pd.to_datetime(df['date'], format='%d.%m.%Y', errors='coerce')

    # Filter by date range
    mask = (df['date'] >= start_date) & (df['date'] <= end_date)
    df_filtered = df.loc[mask]

    if df_filtered.empty:
        return {
            'avg_calories': 0,
            'avg_protein': 0,
            'avg_carbs': 0,
            'avg_fat': 0,
            'total_days': 0,
            'total_meals': 0
        }

    # Group by date and calculate daily totals
    daily_totals = df_filtered.groupby('date').agg({
        'kcal': 'sum',
        'protein': 'sum',
        'carb': 'sum',
        'fat': 'sum'
    })

    return {
        'avg_calories': round(daily_totals['kcal'].mean(), 0),
        'avg_protein': round(daily_totals['protein'].mean(), 1),
        'avg_carbs': round(daily_totals['carb'].mean(), 1),
        'avg_fat': round(daily_totals['fat'].mean(), 1),
        'total_days': len(daily_totals),
        'total_meals': len(df_filtered)
    }

def process_daily_nutrition(consumption, start_date, end_date):
    """Process consumption data for daily nutrition charts"""
    if not consumption:
        return {'dates': [], 'calories': [], 'protein': [], 'carbs': [], 'fat': []}

    df = pd.DataFrame(consumption)
    df['date'] = pd.to_datetime(df['date'], format='%d.%m.%Y', errors='coerce')

    # Filter by date range
    mask = (df['date'] >= start_date) & (df['date'] <= end_date)
    df_filtered = df.loc[mask]

    if df_filtered.empty:
        return {'dates': [], 'calories': [], 'protein': [], 'carbs': [], 'fat': []}

    # Group by date
    daily_totals = df_filtered.groupby('date').agg({
        'kcal': 'sum',
        'protein': 'sum',
        'carb': 'sum',
        'fat': 'sum'
    }).reset_index()

    # Sort by date
    daily_totals = daily_totals.sort_values('date')

    return {
        'dates': daily_totals['date'].dt.strftime('%Y-%m-%d').tolist(),
        'calories': daily_totals['kcal'].tolist(),
        'protein': daily_totals['protein'].tolist(),
        'carbs': daily_totals['carb'].tolist(),
        'fat': daily_totals['fat'].tolist()
    }

def process_weight_trend(weights_data, start_date, end_date):
    """Process weight data for trend chart"""
    if not weights_data:
        return {'dates': [], 'weights': []}

    df = pd.DataFrame(weights_data)
    df['date'] = pd.to_datetime(df['date'], format='%d.%m.%Y', errors='coerce')

    # Filter by date range
    mask = (df['date'] >= start_date) & (df['date'] <= end_date)
    df_filtered = df.loc[mask]

    if df_filtered.empty:
        return {'dates': [], 'weights': []}

    # Sort by date
    df_filtered = df_filtered.sort_values('date')

    return {
        'dates': df_filtered['date'].dt.strftime('%Y-%m-%d').tolist(),
        'weights': df_filtered['weight'].tolist()
    }

def process_calorie_trend(calories_data, start_date, end_date):
    """Process calorie data for trend chart"""
    if not calories_data:
        return {'dates': [], 'calories': []}

    df = pd.DataFrame(calories_data)
    df['date'] = pd.to_datetime(df['date'], format='%d.%m.%Y', errors='coerce')

    # Filter by date range
    mask = (df['date'] >= start_date) & (df['date'] <= end_date)
    df_filtered = df.loc[mask]

    if df_filtered.empty:
        return {'dates': [], 'calories': []}

    # Sort by date
    df_filtered = df_filtered.sort_values('date')

    return {
        'dates': df_filtered['date'].dt.strftime('%Y-%m-%d').tolist(),
        'calories': df_filtered['calories'].tolist()
    }

def calculate_macro_distribution(consumption, start_date, end_date):
    """Calculate macro distribution for pie chart"""
    if not consumption:
        return {'protein': 0, 'carbs': 0, 'fat': 0}

    df = pd.DataFrame(consumption)
    df['date'] = pd.to_datetime(df['date'], format='%d.%m.%Y', errors='coerce')

    # Filter by date range
    mask = (df['date'] >= start_date) & (df['date'] <= end_date)
    df_filtered = df.loc[mask]

    if df_filtered.empty:
        return {'protein': 0, 'carbs': 0, 'fat': 0}

    # Calculate totals
    total_protein = df_filtered['protein'].sum()
    total_carbs = df_filtered['carb'].sum()
    total_fat = df_filtered['fat'].sum()

    # Convert to calories
    protein_calories = total_protein * 4
    carb_calories = total_carbs * 4
    fat_calories = total_fat * 9

    total_calories = protein_calories + carb_calories + fat_calories

    if total_calories == 0:
        return {'protein': 0, 'carbs': 0, 'fat': 0}

    return {
        'protein': round((protein_calories / total_calories) * 100, 1),
        'carbs': round((carb_calories / total_calories) * 100, 1),
        'fat': round((fat_calories / total_calories) * 100, 1)
    }

def calculate_food_frequency(consumption, start_date, end_date):
    """Calculate most frequently consumed foods"""
    if not consumption:
        return []

    df = pd.DataFrame(consumption)
    df['date'] = pd.to_datetime(df['date'], format='%d.%m.%Y', errors='coerce')

    # Filter by date range
    mask = (df['date'] >= start_date) & (df['date'] <= end_date)
    df_filtered = df.loc[mask]

    if df_filtered.empty:
        return []

    # Count food frequency
    food_counts = df_filtered['ingredient'].value_counts().head(10)

    return [{'food': food, 'count': int(count)} for food, count in food_counts.items()]

def calculate_weekly_averages(consumption, start_date, end_date):
    """Calculate weekly average nutrition"""
    if not consumption:
        return []

    df = pd.DataFrame(consumption)
    df['date'] = pd.to_datetime(df['date'], format='%d.%m.%Y', errors='coerce')

    # Filter by date range
    mask = (df['date'] >= start_date) & (df['date'] <= end_date)
    df_filtered = df.loc[mask]

    if df_filtered.empty:
        return []

    # Add week column
    df_filtered['week'] = df_filtered['date'].dt.isocalendar().week
    df_filtered['year'] = df_filtered['date'].dt.year

    # Group by week
    weekly_averages = df_filtered.groupby(['year', 'week']).agg({
        'kcal': 'mean',
        'protein': 'mean',
        'carb': 'mean',
        'fat': 'mean',
        'date': 'min'
    }).reset_index()

    # Sort by date
    weekly_averages = weekly_averages.sort_values('date')

    return [{
        'week_start': row['date'].strftime('%Y-%m-%d'),
        'avg_calories': round(row['kcal'], 0),
        'avg_protein': round(row['protein'], 1),
        'avg_carbs': round(row['carb'], 1),
        'avg_fat': round(row['fat'], 1)
    } for _, row in weekly_averages.iterrows()]
