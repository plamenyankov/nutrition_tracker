"""
AI Analyzer routes for Cycling Readiness feature.
Handles post-workout AI analysis and analysis history.
"""
from flask import render_template, request, jsonify
from flask_login import login_required, current_user

from .. import cycling_readiness_bp
from .helpers import (
    logger,
    serialize_for_json,
    get_service,
    get_base_context,
)
from models.services.cycling_readiness_service import CyclingReadinessService


# ============== Page Routes ==============

@cycling_readiness_bp.route('/ai-analyzer')
@login_required
def ai_analyzer_page():
    """AI Analyzer page - Detailed workout analysis."""
    service = get_service()
    cycling_workouts = service.get_cycling_workouts(limit=10)
    
    # Check if workout_id is passed in URL
    workout_id = request.args.get('workout_id', type=int)
    selected_workout = None
    
    if workout_id:
        workout = service.get_cycling_workout_by_id(workout_id)
        if workout and workout.get('user_id') == current_user.id:
            selected_workout = workout
    
    context = get_base_context()
    context.update({
        'current_tab': 'ai_analyzer',
        'cycling_workouts': cycling_workouts,
        'selected_workout': selected_workout,
        'workout_id': workout_id
    })
    
    return render_template('cycling_readiness/ai_analyzer.html', **context)


# ============== AI Workout Analysis API ==============

@cycling_readiness_bp.route('/api/ai/analysis/analyze', methods=['POST'])
@login_required
def analyze_workout():
    """
    Analyze a workout using AI (POST to trigger analysis).
    
    Request body:
        {
            "workout_id": <int>,
            "force_regenerate": false
        }
    
    If analysis exists and force_regenerate=false, returns existing analysis.
    Otherwise, generates new AI analysis via OpenAI.
    
    Returns:
        Standardized analysis JSON response
    
    ---
    tags:
      - AI Analysis
    """
    from models.services.ai_analyzer_service import generate_ai_workout_analysis
    
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    workout_id = data.get('workout_id')
    force_regenerate = data.get('force_regenerate', False)
    
    if not workout_id:
        return jsonify({'success': False, 'error': 'workout_id is required'}), 400
    
    try:
        workout_id = int(workout_id)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'workout_id must be an integer'}), 400
    
    service = get_service()
    
    # Validate workout exists and belongs to current user
    workout = service.get_cycling_workout_by_id(workout_id)
    if not workout:
        return jsonify({'success': False, 'error': 'Workout not found'}), 404
    
    # Check workout belongs to current user
    if workout.get('user_id') != current_user.id:
        return jsonify({'success': False, 'error': 'Workout not found'}), 404
    
    # Check for existing analysis (only if not forcing regeneration)
    if not force_regenerate:
        existing_analysis = service.get_analysis_for_workout(workout_id)
        if existing_analysis:
            # Return existing analysis
            formatted = CyclingReadinessService.format_analysis_json(existing_analysis, workout)
            return jsonify({
                'success': True,
                'cached': True,
                'analysis': formatted
            })
    
    try:
        # Generate real AI analysis
        logger.info(f"[API] Generating AI analysis for workout_id={workout_id}, force={force_regenerate}")
        
        saved_analysis = generate_ai_workout_analysis(
            user_id=current_user.id,
            workout_id=workout_id,
            force_regenerate=force_regenerate
        )
        
        formatted = CyclingReadinessService.format_analysis_json(saved_analysis, workout)
        
        return jsonify({
            'success': True,
            'cached': False,
            'analysis': serialize_for_json(formatted)
        })
        
    except ValueError as e:
        logger.error(f"[API] Analysis error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"[API] Unexpected error during analysis: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': 'Failed to generate analysis'}), 500


@cycling_readiness_bp.route('/api/ai/analysis/workout/<int:workout_id>', methods=['GET'])
@login_required
def get_workout_analysis(workout_id):
    """
    Get existing AI analysis for a specific workout.
    
    Returns 404 if no analysis exists (does not generate new one).
    
    ---
    tags:
      - AI Analysis
    """
    service = get_service()
    
    # Validate workout exists and belongs to current user
    workout = service.get_cycling_workout_by_id(workout_id)
    if not workout:
        return jsonify({'success': False, 'error': 'Workout not found'}), 404
    
    # Check workout belongs to current user
    if workout.get('user_id') != current_user.id:
        return jsonify({'success': False, 'error': 'Workout not found'}), 404
    
    # Get existing analysis
    analysis = service.get_analysis_for_workout(workout_id)
    if not analysis:
        return jsonify({'success': False, 'error': 'Analysis not found'}), 404
    
    formatted = CyclingReadinessService.format_analysis_json(analysis, workout)
    
    return jsonify({
        'success': True,
        'analysis': serialize_for_json(formatted)
    })


@cycling_readiness_bp.route('/api/ai/analysis/history', methods=['GET'])
@login_required
def get_analysis_history():
    """
    Get paginated list of AI workout analyses for the current user.
    
    Query params:
        limit: Max results (default 20)
        offset: Pagination offset (default 0)
    
    Returns:
        List of analysis summaries
    
    ---
    tags:
      - AI Analysis
    """
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    # Validate limits
    limit = min(max(1, limit), 100)  # Between 1 and 100
    offset = max(0, offset)
    
    service = get_service()
    
    analyses = service.get_analysis_history(limit=limit, offset=offset)
    total = service.get_analysis_count()
    
    # Format each analysis for response
    formatted_analyses = []
    for a in analyses:
        # Format date
        date_val = a.get('date')
        if hasattr(date_val, 'strftime'):
            a['date'] = date_val.strftime('%Y-%m-%d')
        
        # Format timestamps
        for ts_field in ['created_at', 'updated_at']:
            ts_val = a.get(ts_field)
            if hasattr(ts_val, 'isoformat'):
                a[ts_field] = ts_val.isoformat()
        
        # Build workout summary from joined data
        duration_sec = a.get('workout_duration_sec')
        workout_summary = {
            'duration_min': int(duration_sec / 60) if duration_sec else None,
            'avg_power_w': round(a.get('workout_avg_power_w'), 1) if a.get('workout_avg_power_w') else None,
            'avg_hr_bpm': a.get('workout_avg_hr_bpm')
        }
        
        formatted_analyses.append({
            'workout_id': a.get('workout_id'),
            'date': a.get('date'),
            'overall_score': a.get('overall_score'),
            'compliance_score': a.get('compliance_score'),
            'execution_label': a.get('execution_label'),
            'fatigue_risk': a.get('fatigue_risk'),
            'notes_short': a.get('notes_short'),
            'workout_summary': workout_summary,
            'created_at': a.get('created_at'),
            'updated_at': a.get('updated_at')
        })
    
    return jsonify({
        'success': True,
        'analyses': formatted_analyses,
        'pagination': {
            'limit': limit,
            'offset': offset,
            'total': total,
            'has_more': offset + limit < total
        }
    })



