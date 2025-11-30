"""
Routes for Cycling & Readiness feature.
Includes page routes and API endpoints.
"""
import io
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user


def serialize_for_json(obj):
    """Convert non-JSON-serializable objects to JSON-safe types"""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [serialize_for_json(item) for item in obj]
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.strftime('%Y-%m-%d')
    if isinstance(obj, timedelta):
        return int(obj.total_seconds())
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, bytes):
        return obj.decode('utf-8', errors='ignore')
    return obj

from . import cycling_readiness_bp
from models.services.cycling_readiness_service import CyclingReadinessService
from models.services.openai_extraction import (
    extract_from_image,
    extract_batch,
    extract_cycling_workout_from_image,
    extract_sleep_summary_from_image,
    CyclingWorkoutPayload,
    SleepSummaryPayload,
    UnknownPayload,
    BatchExtractionResult
)

logger = logging.getLogger(__name__)


# ============== Missing Fields Detection ==============

# Fields that should never be zero (0 is as bad as null for these)
CYCLING_NUMERIC_FIELDS = [
    'duration_sec', 'distance_km', 'avg_power_w', 'max_power_w', 
    'normalized_power_w', 'tss', 'intensity_factor', 'avg_heart_rate', 
    'max_heart_rate', 'avg_cadence', 'kcal_active', 'kcal_total'
]

SLEEP_NUMERIC_FIELDS = [
    'total_sleep_minutes', 'deep_sleep_minutes', 'wakeups_count',
    'min_heart_rate', 'avg_heart_rate', 'max_heart_rate'
]

# Fields where 0 is invalid (should be treated as missing)
ZERO_INVALID_FIELDS = {
    'avg_heart_rate', 'max_heart_rate', 'min_heart_rate',
    'avg_power_w', 'max_power_w', 'normalized_power_w',
    'duration_sec', 'total_sleep_minutes'
}


def detect_missing_numeric_fields(data: dict, field_list: list) -> list:
    """
    Detect which numeric fields are missing or invalid (null or 0 for certain fields).
    Returns list of field names that need user input.
    """
    missing = []
    for field in field_list:
        value = data.get(field)
        if value is None:
            missing.append(field)
        elif field in ZERO_INVALID_FIELDS and value == 0:
            missing.append(field)
    return missing


def get_service():
    """Get CyclingReadinessService instance for current user"""
    user_id = current_user.id if current_user.is_authenticated else None
    return CyclingReadinessService(user_id=user_id)


# ============== Page Routes ==============

@cycling_readiness_bp.route('/')
@login_required
def dashboard():
    """
    Main Cycling & Readiness dashboard page.
    Shows cycling workouts, readiness entries, and charts.
    """
    service = get_service()

    # Get recent data
    cycling_workouts = service.get_cycling_workouts(limit=10)
    readiness_entries = service.get_readiness_entries(limit=14)
    cycling_stats = service.get_cycling_stats(days=30)

    # Get chart data
    cycling_chart = service.get_cycling_chart_data(days=30)
    readiness_chart = service.get_readiness_chart_data(days=30)

    return render_template(
        'cycling_readiness/dashboard.html',
        cycling_workouts=cycling_workouts,
        readiness_entries=readiness_entries,
        cycling_stats=cycling_stats,
        cycling_chart=cycling_chart,
        readiness_chart=readiness_chart,
        today=datetime.now().strftime('%Y-%m-%d')
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
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({'error': 'Date parameter required'}), 400
    
    service = get_service()
    
    # Get all data for this date
    cycling_workout = service.get_cycling_workout_by_date(date_str)
    readiness_entry = service.get_readiness_by_date(date_str)
    sleep_summary = service.get_sleep_summary_by_date(date_str)
    
    # Detect missing fields for each
    missing = {
        'cycling': [],
        'readiness': [],
        'sleep': []
    }
    
    if cycling_workout:
        missing['cycling'] = detect_missing_numeric_fields(cycling_workout, CYCLING_NUMERIC_FIELDS)
    
    if readiness_entry:
        readiness_fields = ['energy', 'mood', 'muscle_fatigue', 'sleep_minutes', 'deep_sleep_minutes']
        missing['readiness'] = [f for f in readiness_fields if not readiness_entry.get(f)]
    
    if sleep_summary:
        missing['sleep'] = detect_missing_numeric_fields(sleep_summary, SLEEP_NUMERIC_FIELDS)
    
    return jsonify({
        'success': True,
        'date': date_str,
        'cycling_workout': serialize_for_json(cycling_workout),
        'readiness_entry': serialize_for_json(readiness_entry),
        'sleep_summary': serialize_for_json(sleep_summary),
        'missing': missing,
        'has_data': bool(cycling_workout or readiness_entry or sleep_summary)
    })


@cycling_readiness_bp.route('/api/cycling/stats', methods=['GET'])
@login_required
def get_cycling_stats():
    """Get cycling statistics"""
    days = request.args.get('days', 30, type=int)
    service = get_service()
    stats = service.get_cycling_stats(days=days)
    return jsonify(stats)


# ============== Bundle Import API Route ==============

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
                wakeups_count=cs.wakeups,
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
                'wakeups_count': cs.wakeups,
                'min_heart_rate': cs.min_hr
            }
            
            # Update readiness entry
            readiness = service.update_readiness_from_sleep(cs.date, sleep_payload)
            if readiness:
                if readiness.get('date'):
                    readiness['date'] = readiness['date'].strftime('%Y-%m-%d') if hasattr(readiness['date'], 'strftime') else str(readiness['date'])
                readiness_results.append(readiness)
        
        # ============== Build response ==============
        canonical_date = batch_result.canonical_workout.date or batch_result.canonical_sleep.date or datetime.now().strftime('%Y-%m-%d')
        
        # Count image types
        cycling_count = sum(1 for r in batch_result.image_results if r.type in ['cycling_power', 'watch_workout'])
        sleep_count = sum(1 for r in batch_result.image_results if r.type == 'sleep_summary')
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
                'wakeups_count': cs_dict.get('wakeups'),
                'min_heart_rate': cs_dict.get('min_hr'),
                'avg_heart_rate': cs_dict.get('avg_hr'),
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
            'summary': {
                'cycling_images': cycling_count,
                'sleep_images': sleep_count,
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
            wakeups_count=payload.wakeups_count,
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
        entry_id, morning_score = service.create_or_update_readiness(
            date=data['date'],
            energy=int(data['energy']),
            mood=int(data['mood']),
            muscle_fatigue=int(data['muscle_fatigue']),
            hrv_status=int(data.get('hrv_status', 0)),
            rhr_status=int(data.get('rhr_status', 0)),
            min_hr_status=int(data.get('min_hr_status', 0)),
            sleep_minutes=int(data.get('sleep_minutes', 0)) if data.get('sleep_minutes') else 0,
            deep_sleep_minutes=int(data.get('deep_sleep_minutes', 0)) if data.get('deep_sleep_minutes') else 0,
            wakeups_count=int(data.get('wakeups_count', 0)) if data.get('wakeups_count') else 0,
            stress_level=int(data.get('stress_level', 2)),
            symptoms_flag=bool(data.get('symptoms_flag', False)),
            evening_note=data.get('evening_note')
        )

        return jsonify({
            'success': True,
            'entry_id': entry_id,
            'morning_score': morning_score
        })

    except Exception as e:
        logger.error(f"Error saving readiness: {e}")
        return jsonify({'error': 'Failed to save readiness entry'}), 500


@cycling_readiness_bp.route('/api/readiness', methods=['GET'])
@login_required
def get_readiness_entries():
    """
    Get readiness entries list.
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
        description: List of readiness entries
    """
    limit = request.args.get('limit', 14, type=int)
    service = get_service()
    entries = service.get_readiness_entries(limit=limit)

    # Convert dates to strings for JSON serialization
    for e in entries:
        if e.get('date'):
            e['date'] = e['date'].strftime('%Y-%m-%d') if hasattr(e['date'], 'strftime') else str(e['date'])

    return jsonify({'entries': entries})


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


@cycling_readiness_bp.route('/api/cycling/chart', methods=['GET'])
@login_required
def get_cycling_chart_data():
    """Get cycling data formatted for charts"""
    days = request.args.get('days', 30, type=int)
    service = get_service()
    chart_data = service.get_cycling_chart_data(days=days)
    return jsonify(chart_data)

