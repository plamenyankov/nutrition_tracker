"""
Analytics routes for Cycling Readiness feature.
Handles KPIs, trends, efficiency metrics, and body weights.
"""
from flask import render_template, request, jsonify
from flask_login import login_required

from .. import cycling_readiness_bp
from .helpers import (
    logger,
    serialize_for_json,
    get_service,
    get_base_context,
)


# ============== Page Routes ==============

@cycling_readiness_bp.route('/analytics')
@login_required
def analytics_page():
    """Analytics page - KPIs, charts, and trends."""
    service = get_service()
    cycling_chart = service.get_cycling_chart_data(days=30)
    readiness_chart = service.get_readiness_chart_data(days=30)
    
    context = get_base_context()
    context.update({
        'current_tab': 'analytics',
        'cycling_chart': cycling_chart,
        'readiness_chart': readiness_chart
    })
    
    return render_template('cycling_readiness/analytics.html', **context)


# ============== Analytics KPI API ==============

@cycling_readiness_bp.route('/api/analytics/kpis', methods=['GET'])
@login_required
def get_analytics_kpis():
    """
    Get KPI data for the Analytics dashboard.
    
    Returns:
        JSON with:
        - acute_load_7d: 7-day TSS total and daily average
        - chronic_load_42d: 42-day weekly TSS average
        - hrv_trend: Today's HRV vs 30-day baseline
        - rhr_trend: Today's RHR vs 30-day baseline
        - z2_power_trend: 7-day vs 30-day Z2 power average
    """
    service = get_service()
    
    try:
        kpis = service.get_analytics_kpis()
        return jsonify({
            'success': True,
            'kpis': serialize_for_json(kpis)
        })
    except Exception as e:
        logger.error(f"Error fetching KPIs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@cycling_readiness_bp.route('/api/analytics/efficiency-vo2', methods=['GET'])
@login_required
def get_efficiency_vo2_data():
    """
    Get Efficiency Index, VO2 Index, Fatigue Ratio, and Aerobic Efficiency data.
    
    Returns:
        JSON with:
        - efficiency_timeseries: Per-workout EI (power/HR) data
        - efficiency_rolling_7d: 7-day rolling average EI
        - vo2_weekly: Weekly VO2-style index with dynamic weight
        - fatigue_ratio: HR drift per workout
        - aerobic_efficiency: Z2 Power / HRV ratio
    """
    service = get_service()
    
    try:
        data = service.get_efficiency_vo2_data()
        return jsonify({
            'success': True,
            **serialize_for_json(data)
        })
    except Exception as e:
        logger.error(f"Error fetching efficiency/VO2 data: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'efficiency_timeseries': [],
            'efficiency_rolling_7d': [],
            'vo2_weekly': [],
            'fatigue_ratio': [],
            'aerobic_efficiency': []
        }), 500


@cycling_readiness_bp.route('/api/analytics/weights', methods=['GET'])
@login_required
def get_body_weights():
    """
    Get body weight entries for the last 12 weeks.
    
    Returns:
        JSON with list of weight entries
    """
    service = get_service()
    weeks = request.args.get('weeks', 12, type=int)
    
    try:
        weights = service.get_body_weights(weeks=weeks)
        return jsonify({
            'success': True,
            'weights': serialize_for_json(weights)
        })
    except Exception as e:
        logger.error(f"Error fetching body weights: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'weights': []
        }), 500


@cycling_readiness_bp.route('/api/analytics/weights', methods=['POST'])
@login_required
def save_body_weight():
    """
    Save or update body weight entry for a specific date.
    
    Request body:
        { "date": "2025-11-24", "weight_kg": 87.0 }
    
    Returns:
        JSON with success status and saved entry
    """
    service = get_service()
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    date_str = data.get('date')
    weight_kg = data.get('weight_kg')
    
    if not date_str or weight_kg is None:
        return jsonify({'success': False, 'error': 'Missing date or weight_kg'}), 400
    
    try:
        weight_kg = float(weight_kg)
        if weight_kg <= 0 or weight_kg > 300:
            return jsonify({'success': False, 'error': 'Invalid weight value'}), 400
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'Invalid weight value'}), 400
    
    try:
        result = service.save_body_weight(date_str, weight_kg)
        return jsonify(serialize_for_json(result))
    except Exception as e:
        logger.error(f"Error saving body weight: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500



