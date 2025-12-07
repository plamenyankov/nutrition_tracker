"""
AI Coach routes for Cycling Readiness feature.
Handles training context and AI-generated training recommendations.
"""
from datetime import datetime, date as date_type
from flask import render_template, request, jsonify
from flask_login import login_required, current_user

from .. import cycling_readiness_bp
from .helpers import (
    logger,
    get_service,
    get_base_context,
)


# ============== Page Routes ==============

@cycling_readiness_bp.route('/coach')
@login_required
def coach_page():
    """AI Coach page - Training recommendations."""
    service = get_service()
    cycling_workouts = service.get_cycling_workouts(limit=5)
    
    # Check if date is passed in URL for auto-analyze
    selected_date = request.args.get('date')
    
    context = get_base_context()
    context.update({
        'current_tab': 'coach',
        'cycling_workouts': cycling_workouts,
        'selected_date': selected_date,
        'auto_analyze': selected_date is not None
    })
    
    return render_template('cycling_readiness/coach.html', **context)


# ============== Training Context API ==============

@cycling_readiness_bp.route('/api/training-context', methods=['GET'])
@login_required
def get_training_context():
    """
    Get comprehensive training context for AI recommendations.
    
    Aggregates data from readiness entries, sleep summaries, cardio metrics,
    and historical workout data to build a context object for any evaluation date.
    
    Note: The 'day' section does NOT include cycling workouts for the evaluation date,
    as those are used later to compare planned vs actual training.
    
    ---
    tags:
      - Training
    parameters:
      - name: date
        in: query
        type: string
        format: date
        required: false
        description: Target/evaluation date (YYYY-MM-DD). Defaults to today.
    responses:
      200:
        description: Training context object with standardized structure
        schema:
          type: object
          properties:
            success:
              type: boolean
            date:
              type: string
              format: date
            context:
              type: object
              properties:
                evaluation_date:
                  type: string
                day:
                  type: object
                  description: Readiness, sleep, and cardio for evaluation_date (no workout)
                history_7d:
                  type: array
                  description: Summary of D-7 to D-1
                baseline_30d:
                  type: object
                  description: Aggregated stats from D-30 to D-1
      400:
        description: Invalid date format
    """
    # Get target date from query params (default to today)
    date_str = request.args.get('date')
    
    if date_str:
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid date format. Use YYYY-MM-DD.'
            }), 400
    else:
        target_date = date_type.today()
    
    try:
        service = get_service()
        context = service.build_training_context(target_date)
        
        return jsonify({
            'success': True,
            'date': target_date.strftime('%Y-%m-%d'),
            'context': context
        })
    
    except Exception as e:
        logger.error(f"Error building training context: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'Failed to build training context'
        }), 500


@cycling_readiness_bp.route('/api/training-recommendation', methods=['GET'])
@login_required
def get_training_recommendation_api():
    """
    Get AI-generated training recommendation for a specific date.
    
    Uses the training context (readiness, sleep, cardio, workout history)
    to generate a personalized training recommendation via OpenAI.
    
    If a recommendation already exists for the date, returns the stored one.
    Use refresh=true to force regeneration.
    
    ---
    tags:
      - Training
    parameters:
      - name: date
        in: query
        type: string
        format: date
        required: false
        description: Target date (YYYY-MM-DD). Defaults to today.
      - name: refresh
        in: query
        type: string
        required: false
        description: Set to "true" to force regeneration (ignores stored recommendation)
    responses:
      200:
        description: Training recommendation
        schema:
          type: object
          properties:
            success:
              type: boolean
            cached:
              type: boolean
              description: True if returned from storage, False if freshly generated
            recommendation:
              type: object
              properties:
                date:
                  type: string
                day_type:
                  type: string
                reason_short:
                  type: string
                session_plan:
                  type: object
                flags:
                  type: object
      400:
        description: Invalid date format
      500:
        description: Failed to generate recommendation
    """
    from models.services.training_recommendation import (
        generate_training_recommendation,
        get_training_recommendation,
        get_recommendation_summary
    )
    
    # Get target date from query params (default to today)
    date_str = request.args.get('date')
    
    if date_str:
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid date format. Use YYYY-MM-DD.'
            }), 400
    else:
        target_date = date_type.today()
    
    # Check if refresh is requested
    force_refresh = request.args.get('refresh', '').lower() == 'true'
    
    try:
        # Generate or retrieve the recommendation
        # If force_refresh=False, this will return cached recommendation if it exists
        recommendation = generate_training_recommendation(
            user_id=current_user.id,
            target_date=target_date,
            force_refresh=force_refresh
        )
        
        # Get human-readable summary
        summary = get_recommendation_summary(recommendation)
        
        return jsonify({
            'success': True,
            'date': target_date.strftime('%Y-%m-%d'),
            'refreshed': force_refresh,
            'recommendation': recommendation.to_dict(),
            'summary': summary
        })
    
    except ValueError as e:
        logger.error(f"Recommendation parsing error: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to parse AI response: {str(e)}'
        }), 500
    
    except Exception as e:
        logger.error(f"Error generating training recommendation: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Failed to generate recommendation: {str(e)}'
        }), 500



