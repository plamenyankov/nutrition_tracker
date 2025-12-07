"""
Workout routes for Cycling Readiness feature.
Handles workout CRUD, screenshot import, batch import, and day summary.
"""
import csv
from io import StringIO
from datetime import datetime
from flask import render_template, request, jsonify, redirect, url_for, Response
from flask_login import login_required, current_user

from .. import cycling_readiness_bp
from .helpers import (
    logger,
    serialize_for_json,
    get_service,
    get_base_context,
    detect_missing_numeric_fields,
    CYCLING_NUMERIC_FIELDS,
    SLEEP_NUMERIC_FIELDS
)
from models.services.openai_extraction import (
    extract_batch,
    extract_cycling_workout_from_image,
)


# ============== Page Routes ==============

@cycling_readiness_bp.route('/')
@login_required
def dashboard():
    """Redirect to workouts page (default tab)."""
    return redirect(url_for('cycling_readiness.workouts_page'))


@cycling_readiness_bp.route('/workouts')
@login_required
def workouts_page():
    """Workouts page - Import screenshots and view workout history."""
    service = get_service()
    cycling_workouts = service.get_cycling_workouts(limit=20)
    
    context = get_base_context()
    context.update({
        'current_tab': 'workouts',
        'cycling_workouts': cycling_workouts
    })
    
    return render_template('cycling_readiness/workouts.html', **context)


@cycling_readiness_bp.route('/expanded')
@login_required
def expanded_table():
    """
    Expanded table view showing all data across all dates.
    Displays cycling, readiness, and sleep data in a horizontal date-oriented table.
    """
    days = request.args.get('days', 90, type=int)
    from_date = request.args.get('from')
    to_date = request.args.get('to')
    
    return render_template(
        'cycling_readiness/expanded_table.html',
        days=days,
        from_date=from_date,
        to_date=to_date
    )


# ============== Expanded Table API ==============

@cycling_readiness_bp.route('/api/expanded-data', methods=['GET'])
@login_required
def get_expanded_data():
    """
    Get all data for expanded table view.
    Returns combined cycling, readiness, and sleep data per date.
    
    Query params:
        days: Number of days to look back (default 90)
        from: Start date (YYYY-MM-DD)
        to: End date (YYYY-MM-DD)
        missing_only: If true, only return days with missing data
    """
    days = request.args.get('days', 90, type=int)
    from_date = request.args.get('from')
    to_date = request.args.get('to')
    missing_only = request.args.get('missing_only', 'false').lower() == 'true'
    
    service = get_service()
    data = service.get_expanded_data(days=days, from_date=from_date, to_date=to_date)
    
    # Filter to only days with missing data if requested
    if missing_only:
        data = [
            row for row in data 
            if row['missing_cycling'] or row['missing_readiness'] or row['missing_sleep']
            or not row['has_cycling'] or not row['has_readiness'] or not row['has_sleep']
        ]
    
    return jsonify({
        'success': True,
        'data': serialize_for_json(data),
        'count': len(data)
    })


@cycling_readiness_bp.route('/api/expanded-export', methods=['GET'])
@login_required
def export_expanded_csv():
    """
    Export expanded data as CSV file.
    
    Query params same as expanded-data endpoint.
    """
    days = request.args.get('days', 90, type=int)
    from_date = request.args.get('from')
    to_date = request.args.get('to')
    
    service = get_service()
    data = service.get_expanded_data(days=days, from_date=from_date, to_date=to_date)
    
    # Create CSV in memory
    output = StringIO()
    
    # Define columns
    fieldnames = [
        'date',
        # Cycling columns
        'c_duration_sec', 'c_distance_km', 'c_avg_power_w', 'c_max_power_w',
        'c_normalized_power_w', 'c_intensity_factor', 'c_tss',
        'c_avg_heart_rate', 'c_max_heart_rate', 'c_avg_cadence',
        'c_kcal_active', 'c_kcal_total', 'c_source',
        # Readiness columns
        'r_energy', 'r_mood', 'r_muscle_fatigue',
        'r_hrv_status', 'r_rhr_status', 'r_min_hr_status',
        'r_symptoms_flag', 'r_morning_score',
        # Sleep columns
        's_total_sleep_minutes', 's_deep_sleep_minutes', 's_awake_minutes',
        's_min_heart_rate', 's_max_heart_rate', 's_sleep_start', 's_sleep_end',
        # Cardio columns
        'cardio_rhr_bpm', 'cardio_hrv_low', 'cardio_hrv_high'
    ]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    
    for row in data:
        writer.writerow(row)
    
    # Return as CSV response
    output.seek(0)
    filename = f"zyra_cycle_data_{datetime.now().strftime('%Y%m%d')}.csv"
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


# ============== Cycling Workout API Routes ==============

@cycling_readiness_bp.route('/api/cycling/import-image', methods=['POST'])
@login_required
def import_cycling_image():
    """
    Import cycling workout from screenshot using AI extraction.
    ---
    tags:
      - Cycling
    consumes:
      - multipart/form-data
    parameters:
      - name: image
        in: formData
        type: file
        required: true
        description: Screenshot of cycling workout
    responses:
      200:
        description: Successfully extracted and saved workout
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
        payload = extract_cycling_workout_from_image(
            image_file.stream,
            filename=image_file.filename
        )

        # Validate we got at least a date
        if not payload.workout_date:
            return jsonify({
                'error': 'Could not extract workout date from image',
                'extracted': payload.to_dict()
            }), 400

        # Save to database
        service = get_service()
        workout_id = service.create_cycling_workout(
            date=payload.workout_date,
            start_time=payload.start_time,
            source=payload.sport,
            notes=payload.notes,
            duration_sec=payload.duration_sec,
            distance_km=payload.distance_km,
            avg_heart_rate=payload.avg_heart_rate,
            max_heart_rate=payload.max_heart_rate,
            avg_power_w=payload.avg_power_w,
            max_power_w=payload.max_power_w,
            normalized_power_w=payload.normalized_power_w,
            intensity_factor=payload.intensity_factor,
            tss=payload.tss,
            avg_cadence=payload.avg_cadence,
            kcal_active=payload.kcal_active,
            kcal_total=payload.kcal_total
        )

        return jsonify({
            'success': True,
            'workout_id': workout_id,
            'extracted': payload.to_dict()
        })

    except ValueError as e:
        logger.error(f"Extraction error: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error importing cycling image: {e}")
        return jsonify({'error': str(e)}), 500


@cycling_readiness_bp.route('/api/cycling', methods=['GET'])
@login_required
def get_cycling_workouts():
    """
    Get cycling workouts list.
    ---
    tags:
      - Cycling
    parameters:
      - name: limit
        in: query
        type: integer
        default: 30
      - name: offset
        in: query
        type: integer
        default: 0
    responses:
      200:
        description: List of cycling workouts
    """
    limit = request.args.get('limit', 30, type=int)
    offset = request.args.get('offset', 0, type=int)

    service = get_service()
    workouts = service.get_cycling_workouts(limit=limit, offset=offset)

    # Convert dates to strings for JSON serialization
    for w in workouts:
        if w.get('date'):
            w['date'] = w['date'].strftime('%Y-%m-%d') if hasattr(w['date'], 'strftime') else str(w['date'])
        if w.get('start_time'):
            w['start_time'] = str(w['start_time'])

    return jsonify({'workouts': workouts})


@cycling_readiness_bp.route('/api/cycling/<int:workout_id>', methods=['DELETE'])
@login_required
def delete_cycling_workout(workout_id):
    """Delete a cycling workout"""
    service = get_service()
    success = service.delete_cycling_workout(workout_id)

    if success:
        return jsonify({'success': True})
    return jsonify({'error': 'Workout not found'}), 404


@cycling_readiness_bp.route('/api/cycling/<int:workout_id>', methods=['PUT', 'PATCH'])
@login_required
def update_cycling_workout(workout_id):
    """
    Update an existing cycling workout.
    Accepts partial updates - only provided fields will be updated.
    ---
    tags:
      - Cycling
    parameters:
      - name: workout_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        schema:
          type: object
          properties:
            date: {type: string, format: date}
            duration_sec: {type: integer}
            distance_km: {type: number}
            avg_power_w: {type: number}
            max_power_w: {type: number}
            normalized_power_w: {type: number}
            intensity_factor: {type: number}
            tss: {type: number}
            avg_heart_rate: {type: integer}
            max_heart_rate: {type: integer}
            avg_cadence: {type: integer}
            kcal_active: {type: integer}
            kcal_total: {type: integer}
            notes: {type: string}
    responses:
      200:
        description: Workout updated successfully
      404:
        description: Workout not found
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    service = get_service()
    
    # Get existing workout first
    existing = service.get_cycling_workout_by_id(workout_id)
    if not existing:
        return jsonify({'error': 'Workout not found'}), 404
    
    # Build update dict from allowed fields
    allowed_fields = [
        'date', 'start_time', 'source', 'notes', 'duration_sec', 'distance_km',
        'avg_power_w', 'max_power_w', 'normalized_power_w', 'intensity_factor',
        'tss', 'avg_heart_rate', 'max_heart_rate', 'avg_cadence',
        'kcal_active', 'kcal_total'
    ]
    
    updates = {}
    for field in allowed_fields:
        if field in data:
            # Convert empty strings to None for numeric fields
            value = data[field]
            if value == '' or value == 'null':
                value = None
            updates[field] = value
    
    if not updates:
        return jsonify({'error': 'No valid fields to update'}), 400
    
    # Perform update
    success = service.update_cycling_workout(workout_id, **updates)
    
    if success:
        # Fetch updated workout
        updated = service.get_cycling_workout_by_id(workout_id)
        return jsonify({
            'success': True,
            'workout': serialize_for_json(updated)
        })
    
    return jsonify({'error': 'Failed to update workout'}), 500


@cycling_readiness_bp.route('/api/cycling/<int:workout_id>', methods=['GET'])
@login_required
def get_cycling_workout(workout_id):
    """Get a single cycling workout by ID"""
    service = get_service()
    workout = service.get_cycling_workout_by_id(workout_id)
    
    if not workout:
        return jsonify({'error': 'Workout not found'}), 404
    
    return jsonify({
        'success': True,
        'workout': serialize_for_json(workout)
    })


@cycling_readiness_bp.route('/api/day-summary', methods=['GET'])
@login_required
def get_day_summary():
    """
    Get all data for a specific date: cycling workout, readiness entry, and sleep summary.
    Also returns which fields are missing for each record type.
    ---
    tags:
      - Day Summary
    parameters:
      - name: date
        in: query
        type: string
        format: date
        required: true
        description: Date in YYYY-MM-DD format
    responses:
      200:
        description: Day summary data
    """
    from models.services.training_recommendation import get_training_recommendation as get_rec
    
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({'error': 'Date parameter required'}), 400
    
    service = get_service()
    
    # Get all data for this date
    cycling_workout = service.get_cycling_workout_by_date(date_str)
    readiness_entry = service.get_readiness_by_date(date_str)
    sleep_summary = service.get_sleep_summary_by_date(date_str)
    cardio_metrics = service.get_cardio_metrics_for_date(date_str)
    
    # Detect missing fields for each
    missing = {
        'cycling': [],
        'readiness': [],
        'sleep': [],
        'cardio': []
    }
    
    if cycling_workout:
        missing['cycling'] = detect_missing_numeric_fields(cycling_workout, CYCLING_NUMERIC_FIELDS)
    
    if readiness_entry:
        readiness_fields = ['energy', 'mood', 'muscle_fatigue', 'sleep_minutes', 'deep_sleep_minutes']
        missing['readiness'] = [f for f in readiness_fields if not readiness_entry.get(f)]
    
    if sleep_summary:
        missing['sleep'] = detect_missing_numeric_fields(sleep_summary, SLEEP_NUMERIC_FIELDS)
    
    if cardio_metrics:
        cardio_fields = ['rhr_bpm', 'hrv_low_ms', 'hrv_high_ms']
        missing['cardio'] = [f for f in cardio_fields if not cardio_metrics.get(f)]
    
    # Get training recommendation if exists
    training_recommendation = None
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        rec = get_rec(current_user.id, target_date)
        if rec:
            training_recommendation = rec.to_dict()
    except Exception as e:
        logger.warning(f"Could not fetch training recommendation for {date_str}: {e}")
    
    return jsonify({
        'success': True,
        'date': date_str,
        'cycling_workout': serialize_for_json(cycling_workout),
        'readiness_entry': serialize_for_json(readiness_entry),
        'sleep_summary': serialize_for_json(sleep_summary),
        'cardio_metrics': serialize_for_json(cardio_metrics),
        'training_recommendation': training_recommendation,
        'missing': missing,
        'has_data': bool(cycling_workout or readiness_entry or sleep_summary or cardio_metrics)
    })


@cycling_readiness_bp.route('/api/cycling/stats', methods=['GET'])
@login_required
def get_cycling_stats():
    """Get cycling statistics"""
    days = request.args.get('days', 30, type=int)
    service = get_service()
    stats = service.get_cycling_stats(days=days)
    return jsonify(stats)


@cycling_readiness_bp.route('/api/cycling/chart', methods=['GET'])
@login_required
def get_cycling_chart_data():
    """Get cycling data formatted for charts"""
    days = request.args.get('days', 30, type=int)
    service = get_service()
    chart_data = service.get_cycling_chart_data(days=days)
    return jsonify(chart_data)


# ============== Bundle Import API Route ==============

# Alias route for backwards compatibility (original path used by frontend)
@cycling_readiness_bp.route('/api/extract-batch', methods=['POST'])
@cycling_readiness_bp.route('/api/cycle/import-bundle', methods=['POST'])
@login_required
def import_bundle():
    """
    Import multiple screenshots at once (cycling, sleep, etc.).
    Uses SINGLE OpenAI API call for all images with AI-powered merging.
    ---
    tags:
      - Bundle Import
    consumes:
      - multipart/form-data
    parameters:
      - name: images
        in: formData
        type: file
        required: true
        description: One or more screenshots (max 4)
    responses:
      200:
        description: Successfully processed bundle
      400:
        description: Invalid request or extraction failed
    """
    if 'images' not in request.files:
        return jsonify({'error': 'No image files provided'}), 400

    files = request.files.getlist('images')
    if not files or all(f.filename == '' for f in files):
        return jsonify({'error': 'No files selected'}), 400

    try:
        service = get_service()
        
        # Prepare images for batch extraction
        image_tuples = []
        for file in files:
            if file.filename == '':
                continue
            # Reset file pointer
            file.stream.seek(0)
            image_tuples.append((file.stream, file.filename))
        
        if not image_tuples:
            return jsonify({'error': 'No valid files selected'}), 400
        
        logger.info(f"[BUNDLE] Processing {len(image_tuples)} images: {[t[1] for t in image_tuples]}")
        
        # ============== SINGLE API CALL for all images ==============
        batch_result = extract_batch(image_tuples)
        
        # Log batch results
        logger.info(f"[BUNDLE] Batch extraction complete:")
        logger.info(f"[BUNDLE]   - Images: {len(batch_result.image_results)}")
        for r in batch_result.image_results:
            logger.info(f"[BUNDLE]   - {r.filename}: type={r.type}, confidence={r.confidence:.2f}")
        if batch_result.canonical_workout.date:
            cw = batch_result.canonical_workout
            logger.info(f"[BUNDLE]   - Canonical workout: date={cw.date}, power={cw.avg_power}W, HR={cw.avg_hr}")
        if batch_result.canonical_sleep.date:
            cs = batch_result.canonical_sleep
            logger.info(f"[BUNDLE]   - Canonical sleep: date={cs.date}, total={cs.total_sleep_minutes}min")
        if batch_result.errors:
            logger.warning(f"[BUNDLE]   - Errors: {batch_result.errors}")
        
        # Check for extraction errors
        if batch_result.errors and not batch_result.canonical_workout.date and not batch_result.canonical_sleep.date:
            return jsonify({
                'error': 'Extraction failed',
                'details': batch_result.errors
            }), 400
        
        # ============== Save canonical workout ==============
        cycling_result = None
        if batch_result.canonical_workout.date:
            cw = batch_result.canonical_workout
            
            # Convert duration_minutes to seconds
            duration_sec = int(cw.duration_minutes * 60) if cw.duration_minutes else None
            
            # Create payload dict for merge function
            cycling_payload = {
                'workout_date': cw.date,
                'sport': 'indoor_cycle',
                'duration_sec': duration_sec,
                'avg_power_w': cw.avg_power,
                'max_power_w': cw.max_power,
                'normalized_power_w': cw.normalized_power,
                'avg_heart_rate': cw.avg_hr,
                'max_heart_rate': cw.max_hr,
                'avg_cadence': cw.cadence_avg,
                'max_cadence': cw.cadence_max,
                'distance_km': cw.distance_km,
                'kcal_active': cw.calories_active,
                'kcal_total': cw.calories_total,
                'tss': cw.tss,
                'intensity_factor': cw.intensity_factor
            }
            
            workout_id, merged_data = service.merge_cycling_workout(cw.date, [cycling_payload])
            cycling_result = merged_data
        
        # ============== Save canonical sleep ==============
        readiness_results = []
        if batch_result.canonical_sleep.date:
            cs = batch_result.canonical_sleep
            
            # Save sleep summary
            service.save_sleep_summary(
                date=cs.date,
                sleep_start_time=cs.sleep_start,
                sleep_end_time=cs.sleep_end,
                total_sleep_minutes=cs.total_sleep_minutes,
                deep_sleep_minutes=cs.deep_sleep_minutes,
                awake_minutes=cs.awake_minutes,
                min_heart_rate=cs.min_hr,
                avg_heart_rate=cs.avg_hr,
                max_heart_rate=cs.max_hr,
                notes=None
            )
            
            # Build sleep payload for readiness update
            sleep_payload = {
                'sleep_end_date': cs.date,
                'total_sleep_minutes': cs.total_sleep_minutes,
                'deep_sleep_minutes': cs.deep_sleep_minutes,
                'awake_minutes': cs.awake_minutes,
                'min_heart_rate': cs.min_hr
            }
            
            # Update readiness entry
            readiness = service.update_readiness_from_sleep(cs.date, sleep_payload)
            if readiness:
                if readiness.get('date'):
                    readiness['date'] = readiness['date'].strftime('%Y-%m-%d') if hasattr(readiness['date'], 'strftime') else str(readiness['date'])
                readiness_results.append(readiness)
        
        # ============== Process cardio_series images ==============
        cardio_processed = []
        for img_result in batch_result.image_results:
            if img_result.type == 'cardio_series':
                # Extract cardio series data from fields
                fields = img_result.fields
                metric = fields.get('metric', '')
                entries = fields.get('entries', [])
                
                logger.info(f"[BUNDLE] Processing cardio_series: metric={metric}, entries={len(entries)}")
                
                # Process each entry
                for entry in entries:
                    date_str = entry.get('date')
                    low = entry.get('low')
                    high = entry.get('high')
                    
                    if not date_str:
                        continue
                    
                    try:
                        if metric == 'resting_heart_rate':
                            # RHR is a single value per day, use low (which equals high)
                            rhr_value = int(low) if low is not None else None
                            service.upsert_cardio_metrics(
                                date=date_str,
                                rhr_bpm=rhr_value
                            )
                            # Recalculate readiness score if entry exists for this date
                            service.recalculate_readiness_score(date_str)
                            cardio_processed.append({
                                'date': date_str,
                                'metric': 'rhr',
                                'value': rhr_value
                            })
                            logger.info(f"[BUNDLE] Saved RHR for {date_str}: {rhr_value} bpm")
                        elif metric == 'hrv':
                            # HRV is a range (low to high)
                            hrv_low = int(low) if low is not None else None
                            hrv_high = int(high) if high is not None else None
                            service.upsert_cardio_metrics(
                                date=date_str,
                                hrv_low_ms=hrv_low,
                                hrv_high_ms=hrv_high
                            )
                            # Recalculate readiness score if entry exists for this date
                            service.recalculate_readiness_score(date_str)
                            cardio_processed.append({
                                'date': date_str,
                                'metric': 'hrv',
                                'low': hrv_low,
                                'high': hrv_high
                            })
                            logger.info(f"[BUNDLE] Saved HRV for {date_str}: {hrv_low}-{hrv_high} ms")
                    except Exception as e:
                        logger.error(f"[BUNDLE] Error processing cardio entry {date_str}: {e}")
        
        # ============== Build response ==============
        canonical_date = batch_result.canonical_workout.date or batch_result.canonical_sleep.date or datetime.now().strftime('%Y-%m-%d')
        
        # Count image types
        cycling_count = sum(1 for r in batch_result.image_results if r.type in ['cycling_power', 'watch_workout'])
        sleep_count = sum(1 for r in batch_result.image_results if r.type == 'sleep_summary')
        cardio_count = sum(1 for r in batch_result.image_results if r.type == 'cardio_series')
        unknown_count = sum(1 for r in batch_result.image_results if r.type == 'unknown')
        
        # Detect missing fields for canonical workout/sleep
        workout_missing = []
        sleep_missing = []
        
        if batch_result.canonical_workout.date:
            cw_dict = batch_result.canonical_workout.to_dict()
            # Map canonical workout fields to cycling_workout fields
            mapped_cw = {
                'duration_sec': int(cw_dict.get('duration_minutes') * 60) if cw_dict.get('duration_minutes') else None,
                'distance_km': cw_dict.get('distance_km'),
                'avg_power_w': cw_dict.get('avg_power'),
                'max_power_w': cw_dict.get('max_power'),
                'normalized_power_w': cw_dict.get('normalized_power'),
                'tss': cw_dict.get('tss'),
                'intensity_factor': cw_dict.get('intensity_factor'),
                'avg_heart_rate': cw_dict.get('avg_hr'),
                'max_heart_rate': cw_dict.get('max_hr'),
                'avg_cadence': cw_dict.get('cadence_avg'),
                'kcal_active': cw_dict.get('calories_active'),
                'kcal_total': cw_dict.get('calories_total')
            }
            workout_missing = detect_missing_numeric_fields(mapped_cw, CYCLING_NUMERIC_FIELDS)
        
        if batch_result.canonical_sleep.date:
            cs_dict = batch_result.canonical_sleep.to_dict()
            mapped_cs = {
                'total_sleep_minutes': cs_dict.get('total_sleep_minutes'),
                'deep_sleep_minutes': cs_dict.get('deep_sleep_minutes'),
                'awake_minutes': cs_dict.get('awake_minutes'),
                'min_heart_rate': cs_dict.get('min_hr'),
                'max_heart_rate': cs_dict.get('max_hr')
            }
            sleep_missing = detect_missing_numeric_fields(mapped_cs, SLEEP_NUMERIC_FIELDS)
        
        # Get saved IDs for response
        workout_id = cycling_result.get('id') if cycling_result else None
        
        return jsonify({
            'success': True,
            'canonical_date': canonical_date,
            'extraction_results': [
                {
                    'filename': r.filename,
                    'type': r.type,
                    'confidence': r.confidence,
                    'fields': r.fields
                } for r in batch_result.image_results
            ],
            'cycling_workout': serialize_for_json(cycling_result),
            'workout_id': workout_id,
            'canonical_workout': serialize_for_json(batch_result.canonical_workout.to_dict()),
            'canonical_sleep': serialize_for_json(batch_result.canonical_sleep.to_dict()),
            'readiness_entries': serialize_for_json(readiness_results),
            'missing_fields': {
                'workout': workout_missing,
                'sleep': sleep_missing
            },
            'has_missing_data': len(workout_missing) > 0 or len(sleep_missing) > 0,
            'cardio_processed': cardio_processed,
            'summary': {
                'cycling_images': cycling_count,
                'sleep_images': sleep_count,
                'cardio_images': cardio_count,
                'unknown_images': unknown_count,
                'errors': len(batch_result.errors),
                'api_calls': 1  # Single API call!
            }
        })

    except ValueError as e:
        logger.error(f"Bundle import error: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error processing bundle: {e}")
        return jsonify({'error': str(e)}), 500


# ============== Batch Save API Route (for reviewed/corrected data) ==============

@cycling_readiness_bp.route('/api/batch-save', methods=['POST'])
@login_required
def batch_save():
    """
    Save corrected extraction data after user review.
    This is called after the user fills in missing fields in the review modal.
    ---
    tags:
      - Batch Import
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    extractions = data.get('extractions', [])
    if not extractions:
        return jsonify({'error': 'No extractions to save'}), 400
    
    try:
        service = get_service()
        saved_count = 0
        
        for ext in extractions:
            ext_type = ext.get('type')
            payload = ext.get('payload', {})
            
            if not payload:
                continue
            
            logger.info(f"[BATCH-SAVE] Processing {ext_type} with payload: {payload}")
            
            if ext_type == 'cycling':
                # Save/update cycling workout
                workout_date = payload.get('date') or payload.get('workout_date')
                if not workout_date:
                    logger.warning(f"[BATCH-SAVE] Skipping cycling - no date")
                    continue
                
                # Convert duration_minutes to seconds if present
                duration_sec = None
                if payload.get('duration_minutes'):
                    duration_sec = int(float(payload['duration_minutes']) * 60)
                elif payload.get('duration_sec'):
                    duration_sec = int(payload['duration_sec'])
                
                cycling_payload = {
                    'workout_date': workout_date,
                    'sport': 'indoor_cycle',
                    'duration_sec': duration_sec,
                    'avg_power_w': payload.get('avg_power_w') or payload.get('avg_power'),
                    'max_power_w': payload.get('max_power_w') or payload.get('max_power'),
                    'normalized_power_w': payload.get('normalized_power_w') or payload.get('normalized_power'),
                    'avg_heart_rate': payload.get('avg_heart_rate') or payload.get('avg_hr'),
                    'max_heart_rate': payload.get('max_heart_rate') or payload.get('max_hr'),
                    'avg_cadence': payload.get('avg_cadence') or payload.get('cadence_avg'),
                    'max_cadence': payload.get('max_cadence') or payload.get('cadence_max'),
                    'distance_km': payload.get('distance_km'),
                    'kcal_active': payload.get('kcal_active') or payload.get('calories_active'),
                    'kcal_total': payload.get('kcal_total') or payload.get('calories_total'),
                    'tss': payload.get('tss'),
                    'intensity_factor': payload.get('intensity_factor')
                }
                
                # Remove None values
                cycling_payload = {k: v for k, v in cycling_payload.items() if v is not None}
                
                workout_id, merged_data = service.merge_cycling_workout(workout_date, [cycling_payload])
                logger.info(f"[BATCH-SAVE] Saved cycling workout {workout_id} for {workout_date}")
                saved_count += 1
                
            elif ext_type == 'sleep':
                # Save/update sleep data
                sleep_date = payload.get('date') or payload.get('sleep_end_date')
                if not sleep_date:
                    logger.warning(f"[BATCH-SAVE] Skipping sleep - no date")
                    continue
                
                # Save sleep summary
                service.save_sleep_summary(
                    date=sleep_date,
                    sleep_start_time=payload.get('sleep_start') or payload.get('sleep_start_time'),
                    sleep_end_time=payload.get('sleep_end') or payload.get('sleep_end_time'),
                    total_sleep_minutes=payload.get('total_sleep_minutes'),
                    deep_sleep_minutes=payload.get('deep_sleep_minutes'),
                    awake_minutes=payload.get('awake_minutes'),
                    min_heart_rate=payload.get('min_heart_rate') or payload.get('min_hr'),
                    avg_heart_rate=payload.get('avg_heart_rate') or payload.get('avg_hr'),
                    max_heart_rate=payload.get('max_heart_rate') or payload.get('max_hr'),
                    notes=payload.get('notes')
                )
                
                # Update readiness entry with sleep data
                sleep_payload = {
                    'sleep_end_date': sleep_date,
                    'total_sleep_minutes': payload.get('total_sleep_minutes'),
                    'deep_sleep_minutes': payload.get('deep_sleep_minutes'),
                    'awake_minutes': payload.get('awake_minutes'),
                    'min_heart_rate': payload.get('min_heart_rate') or payload.get('min_hr')
                }
                service.update_readiness_from_sleep(sleep_date, sleep_payload)
                
                logger.info(f"[BATCH-SAVE] Saved sleep data for {sleep_date}")
                saved_count += 1
        
        return jsonify({
            'success': True,
            'saved_count': saved_count
        })
        
    except Exception as e:
        logger.error(f"[BATCH-SAVE] Error: {e}")
        return jsonify({'error': str(e)}), 500



