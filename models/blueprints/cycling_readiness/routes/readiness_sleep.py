"""
Readiness and Sleep routes for Cycling Readiness feature.
Handles morning readiness entries, sleep summaries, and cardio status.
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
from models.services.cycling_readiness_service import CyclingReadinessService
from models.services.openai_extraction import extract_sleep_summary_from_image


# ============== Page Routes ==============

@cycling_readiness_bp.route('/readiness')
@login_required
def readiness_page():
    """Readiness page - Morning readiness form and history."""
    context = get_base_context()
    context.update({
        'current_tab': 'readiness'
    })
    
    return render_template('cycling_readiness/readiness.html', **context)


# ============== Readiness Update API ==============

@cycling_readiness_bp.route('/api/readiness/<int:entry_id>', methods=['PUT', 'PATCH'])
@login_required
def update_readiness_entry(entry_id):
    """
    Update an existing readiness entry.
    Used for editing from Readiness History table.
    
    Accepts partial updates - only provided fields will be updated.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    service = get_service()
    
    # Check entry exists
    existing = service.get_readiness_entry_by_id(entry_id)
    if not existing:
        return jsonify({'error': 'Readiness entry not found'}), 404
    
    # Build update dict from allowed fields
    allowed_fields = [
        'energy', 'mood', 'muscle_fatigue',
        'hrv_status', 'rhr_status', 'min_hr_status',
        'symptoms_flag', 'evening_note'
    ]
    
    updates = {}
    for field in allowed_fields:
        if field in data:
            value = data[field]
            if value == '' or value == 'null':
                value = None
            updates[field] = value
    
    if not updates:
        return jsonify({'error': 'No valid fields to update'}), 400
    
    # Recalculate morning score if we have the necessary data
    merged = {**existing, **updates}
    if merged.get('energy') and merged.get('mood') and merged.get('muscle_fatigue'):
        new_score = CyclingReadinessService.calculate_morning_score(
            energy=merged.get('energy') or 3,
            mood=merged.get('mood') or 2,
            muscle_fatigue=merged.get('muscle_fatigue') or 2,
            hrv_status=merged.get('hrv_status') or 0,
            rhr_status=merged.get('rhr_status') or 0,
            min_hr_status=merged.get('min_hr_status') or 0,
            sleep_minutes=merged.get('sleep_minutes') or 0,
            deep_sleep_minutes=merged.get('deep_sleep_minutes') or 0,
            awake_minutes=merged.get('awake_minutes'),
            symptoms_flag=merged.get('symptoms_flag') or False
        )
        updates['morning_score'] = new_score
    
    # Perform update
    success = service.update_readiness_entry(entry_id, **updates)
    
    if success:
        updated = service.get_readiness_entry_by_id(entry_id)
        return jsonify({
            'success': True,
            'entry': serialize_for_json(updated)
        })
    
    return jsonify({'error': 'Failed to update entry'}), 500


@cycling_readiness_bp.route('/api/readiness/<int:entry_id>', methods=['GET'])
@login_required
def get_readiness_entry(entry_id):
    """Get a single readiness entry by ID"""
    service = get_service()
    entry = service.get_readiness_entry_by_id(entry_id)
    
    if not entry:
        return jsonify({'error': 'Readiness entry not found'}), 404
    
    return jsonify({
        'success': True,
        'entry': serialize_for_json(entry)
    })


@cycling_readiness_bp.route('/api/score-formula', methods=['GET'])
@login_required
def get_score_formula():
    """Get the readiness score formula explanation for UI tooltip"""
    return jsonify({
        'success': True,
        'formula': CyclingReadinessService.SCORE_FORMULA_EXPLANATION
    })


# ============== Sleep Import API Routes ==============

@cycling_readiness_bp.route('/api/sleep/import-image', methods=['POST'])
@login_required
def import_sleep_image():
    """
    Import sleep data from screenshot using AI extraction.
    ---
    tags:
      - Sleep
    consumes:
      - multipart/form-data
    parameters:
      - name: image
        in: formData
        type: file
        required: true
        description: Screenshot of sleep data
    responses:
      200:
        description: Successfully extracted and saved sleep data
      400:
        description: Invalid request or extraction failed
    """
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400

    image_file = request.files['image']
    if image_file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    try:
        # Extract data from image using OpenAI
        payload = extract_sleep_summary_from_image(
            image_file.stream,
            filename=image_file.filename
        )

        # Validate we got at least a date
        sleep_date = payload.sleep_end_date or payload.sleep_start_date
        if not sleep_date:
            return jsonify({
                'error': 'Could not extract sleep date from image',
                'extracted': payload.to_dict()
            }), 400

        # Save to database
        service = get_service()
        summary_id = service.save_sleep_summary(
            date=sleep_date,
            sleep_start_time=payload.sleep_start_time,
            sleep_end_time=payload.sleep_end_time,
            total_sleep_minutes=payload.total_sleep_minutes,
            deep_sleep_minutes=payload.deep_sleep_minutes,
            awake_minutes=payload.awake_minutes,
            min_heart_rate=payload.min_heart_rate,
            avg_heart_rate=payload.avg_heart_rate,
            max_heart_rate=payload.max_heart_rate,
            notes=payload.notes
        )

        return jsonify({
            'success': True,
            'summary_id': summary_id,
            'extracted': payload.to_dict()
        })

    except ValueError as e:
        logger.error(f"Extraction error: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error importing sleep image: {e}")
        return jsonify({'error': str(e)}), 500


# ============== Readiness API Routes ==============

@cycling_readiness_bp.route('/api/readiness', methods=['POST'])
@login_required
def create_readiness():
    """
    Create or update morning readiness entry.
    ---
    tags:
      - Readiness
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - date
            - energy
            - mood
            - muscle_fatigue
          properties:
            date:
              type: string
              format: date
            energy:
              type: integer
              minimum: 1
              maximum: 5
            mood:
              type: integer
              minimum: 1
              maximum: 3
            muscle_fatigue:
              type: integer
              minimum: 1
              maximum: 3
            hrv_status:
              type: integer
              minimum: -1
              maximum: 1
            rhr_status:
              type: integer
              minimum: -1
              maximum: 1
            min_hr_status:
              type: integer
              minimum: -1
              maximum: 1
            sleep_minutes:
              type: integer
            deep_sleep_minutes:
              type: integer
            wakeups_count:
              type: integer
            stress_level:
              type: integer
              minimum: 1
              maximum: 3
            symptoms_flag:
              type: boolean
    responses:
      200:
        description: Successfully saved readiness entry
      400:
        description: Invalid request
    """
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    required_fields = ['date', 'energy', 'mood', 'muscle_fatigue']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    try:
        service = get_service()
        date = data['date']
        
        # Handle manual cardio input (when no screenshot data exists or user overrides)
        manual_rhr = data.get('manual_rhr_bpm')
        manual_hrv_low = data.get('manual_hrv_low_ms')
        manual_hrv_high = data.get('manual_hrv_high_ms')
        rhr_manual_override = data.get('rhr_manual_override', False)
        hrv_manual_override = data.get('hrv_manual_override', False)
        
        if manual_rhr is not None or manual_hrv_low is not None:
            # Save manual cardio values to cardio_daily_metrics
            cardio_updates = {}
            if manual_rhr is not None:
                cardio_updates['rhr_bpm'] = int(manual_rhr)
                cardio_updates['rhr_manual_override'] = True
            if manual_hrv_low is not None and manual_hrv_high is not None:
                cardio_updates['hrv_low_ms'] = int(manual_hrv_low)
                cardio_updates['hrv_high_ms'] = int(manual_hrv_high)
                cardio_updates['hrv_manual_override'] = True
            
            if cardio_updates:
                service.upsert_cardio_metrics(date, **cardio_updates)
                logger.info(f"[READINESS] Saved manual cardio for {date}: {cardio_updates}")
        
        # Handle "reset to auto" - if user explicitly clears manual override
        if data.get('reset_rhr_to_auto'):
            service.upsert_cardio_metrics(date, rhr_manual_override=False)
            logger.info(f"[READINESS] Reset RHR to auto for {date}")
        if data.get('reset_hrv_to_auto'):
            service.upsert_cardio_metrics(date, hrv_manual_override=False)
            logger.info(f"[READINESS] Reset HRV to auto for {date}")
        
        # Determine HRV/RHR status
        # If explicitly provided in request, use those values
        # Otherwise, auto-calculate from cardio data
        hrv_status = data.get('hrv_status')
        rhr_status = data.get('rhr_status')
        
        if hrv_status is None or rhr_status is None:
            # Auto-calculate from cardio data
            cardio_status = service.calculate_hrv_rhr_status(date)
            if hrv_status is None:
                hrv_status = cardio_status.get('hrv_status') or 0
            if rhr_status is None:
                rhr_status = cardio_status.get('rhr_status') or 0
            logger.info(f"[READINESS] Auto-calculated status for {date}: HRV={hrv_status}, RHR={rhr_status}")
        
        # Note: sleep data is imported from screenshots, not entered via form
        # If sleep values are provided, they will be used; otherwise preserved from imports
        entry_id, morning_score = service.create_or_update_readiness(
            date=date,
            energy=int(data['energy']),
            mood=int(data['mood']),
            muscle_fatigue=int(data['muscle_fatigue']),
            hrv_status=int(hrv_status),
            rhr_status=int(rhr_status),
            min_hr_status=int(data.get('min_hr_status', 0)),
            sleep_minutes=int(data.get('sleep_minutes')) if data.get('sleep_minutes') else None,
            deep_sleep_minutes=int(data.get('deep_sleep_minutes')) if data.get('deep_sleep_minutes') else None,
            awake_minutes=int(data.get('awake_minutes')) if data.get('awake_minutes') else None,
            symptoms_flag=bool(data.get('symptoms_flag', False)),
            evening_note=data.get('evening_note')
        )

        # Get full readiness data for the response
        full_data = service.get_full_readiness_data(date)
        
        return jsonify({
            'success': True,
            'entry_id': entry_id,
            'morning_score': morning_score,
            'hrv_status': int(hrv_status),
            'rhr_status': int(rhr_status),
            'readiness': serialize_for_json(full_data.get('readiness')),
            'cardio': full_data.get('cardio')
        })

    except Exception as e:
        logger.error(f"Error saving readiness: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to save readiness entry'}), 500


@cycling_readiness_bp.route('/api/readiness', methods=['GET'])
@login_required
def get_readiness_entries():
    """
    Get readiness entries list with cardio data.
    ---
    tags:
      - Readiness
    parameters:
      - name: limit
        in: query
        type: integer
        default: 14
    responses:
      200:
        description: List of readiness entries with cardio metrics
    """
    limit = request.args.get('limit', 14, type=int)
    service = get_service()
    
    # Use new method that includes cardio data
    entries = service.get_readiness_entries_with_cardio(limit=limit)

    # Convert dates and compute derived fields for frontend
    for e in entries:
        if e.get('date'):
            e['date'] = e['date'].strftime('%Y-%m-%d') if hasattr(e['date'], 'strftime') else str(e['date'])
        
        # Compute sleep_hours from sleep_minutes for frontend
        if e.get('sleep_minutes'):
            e['sleep_hours'] = round(e['sleep_minutes'] / 60, 1)
        else:
            e['sleep_hours'] = None
        
        # Compute hrv_avg from hrv_low_ms and hrv_high_ms for frontend
        hrv_low = e.get('hrv_low_ms')
        hrv_high = e.get('hrv_high_ms')
        if hrv_low is not None and hrv_high is not None:
            e['hrv_avg'] = round((hrv_low + hrv_high) / 2)
        else:
            e['hrv_avg'] = None
        
        # Ensure boolean flags are properly typed
        e['rhr_manual_override'] = bool(e.get('rhr_manual_override', False))
        e['hrv_manual_override'] = bool(e.get('hrv_manual_override', False))
        e['symptoms_flag'] = bool(e.get('symptoms_flag', False))

    return jsonify({'success': True, 'entries': entries})


@cycling_readiness_bp.route('/api/readiness/full', methods=['GET'])
@login_required
def get_full_readiness():
    """
    Get full readiness data for a date including cardio metrics.
    Used for populating the Morning Readiness form.
    ---
    tags:
      - Readiness
    parameters:
      - name: date
        in: query
        type: string
        format: date
        required: true
    responses:
      200:
        description: Full readiness data for the date
    """
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({'error': 'Date parameter required'}), 400
    
    service = get_service()
    data = service.get_full_readiness_data(date_str)
    
    # Serialize for JSON
    if data.get('readiness'):
        data['readiness'] = serialize_for_json(data['readiness'])
    
    return jsonify({
        'success': True,
        **data
    })


@cycling_readiness_bp.route('/api/cardio-status', methods=['GET'])
@login_required
def get_cardio_status():
    """
    Get cardio metrics and calculated HRV/RHR status for a date.
    Used by the Morning Readiness form to auto-fill status values.
    ---
    tags:
      - Cardio
    parameters:
      - name: date
        in: query
        type: string
        format: date
        required: true
    responses:
      200:
        description: Cardio status data
    """
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({'error': 'Date parameter required'}), 400
    
    service = get_service()
    
    # Get calculated status (includes cardio metrics and baseline comparison)
    status = service.calculate_hrv_rhr_status(date_str)
    
    # Also get existing readiness entry if any
    readiness = service.get_readiness_by_date(date_str)
    
    return jsonify({
        'success': True,
        'date': date_str,
        'has_cardio': status.get('has_cardio', False),
        'cardio': {
            'rhr_bpm': status.get('rhr_bpm'),
            'hrv_low_ms': status.get('hrv_low_ms'),
            'hrv_high_ms': status.get('hrv_high_ms'),
            'baseline_rhr': status.get('baseline_rhr'),
            'baseline_hrv': status.get('baseline_hrv')
        },
        'calculated_status': {
            'hrv_status': status.get('hrv_status'),
            'rhr_status': status.get('rhr_status')
        },
        'existing_readiness': serialize_for_json(readiness) if readiness else None
    })


@cycling_readiness_bp.route('/api/readiness/<int:entry_id>', methods=['DELETE'])
@login_required
def delete_readiness_entry(entry_id):
    """Delete a readiness entry"""
    service = get_service()
    success = service.delete_readiness_entry(entry_id)

    if success:
        logger.info(f"[DELETE] Readiness entry {entry_id} deleted")
        return jsonify({'success': True})
    return jsonify({'error': 'Readiness entry not found'}), 404


@cycling_readiness_bp.route('/api/sleep/<int:summary_id>', methods=['DELETE'])
@login_required
def delete_sleep_summary(summary_id):
    """Delete a sleep summary"""
    service = get_service()
    success = service.delete_sleep_summary(summary_id)

    if success:
        logger.info(f"[DELETE] Sleep summary {summary_id} deleted")
        return jsonify({'success': True})
    return jsonify({'error': 'Sleep summary not found'}), 404


@cycling_readiness_bp.route('/api/readiness/chart', methods=['GET'])
@login_required
def get_readiness_chart_data():
    """Get readiness data formatted for charts"""
    days = request.args.get('days', 30, type=int)
    service = get_service()
    chart_data = service.get_readiness_chart_data(days=days)
    return jsonify(chart_data)



