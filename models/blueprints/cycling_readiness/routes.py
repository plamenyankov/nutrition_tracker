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
    extract_cycling_workout_from_image,
    extract_sleep_summary_from_image,
    CyclingWorkoutPayload,
    SleepSummaryPayload,
    UnknownPayload
)

logger = logging.getLogger(__name__)


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
    Automatically classifies each image and merges data.
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
        description: One or more screenshots
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
        cycling_payloads = []
        sleep_payloads = []
        unknown_payloads = []
        extraction_results = []

        # Process each file
        for file in files:
            if file.filename == '':
                continue

            try:
                payload = extract_from_image(file.stream, file.filename)
                result = {
                    'filename': file.filename,
                    'type': payload.type,
                    'data': payload.to_dict()
                }
                extraction_results.append(result)

                if isinstance(payload, CyclingWorkoutPayload):
                    cycling_payloads.append(payload.to_dict())
                elif isinstance(payload, SleepSummaryPayload):
                    sleep_payloads.append(payload.to_dict())
                else:
                    unknown_payloads.append(payload.to_dict())

            except Exception as e:
                logger.error(f"Failed to extract from {file.filename}: {e}")
                extraction_results.append({
                    'filename': file.filename,
                    'type': 'error',
                    'error': str(e)
                })

        # Determine canonical date
        canonical_date = None
        all_workout_dates = [p.get('workout_date') for p in cycling_payloads if p.get('workout_date')]
        all_sleep_dates = [p.get('sleep_end_date') for p in sleep_payloads if p.get('sleep_end_date')]

        if all_workout_dates:
            # Use the latest workout date
            canonical_date = max(all_workout_dates)
            if len(set(all_workout_dates)) > 1:
                logger.warning(f"Multiple workout dates found: {all_workout_dates}. Using: {canonical_date}")
        elif all_sleep_dates:
            canonical_date = max(all_sleep_dates)
        else:
            canonical_date = datetime.now().strftime('%Y-%m-%d')

        # Assign canonical date to payloads with null dates
        for p in cycling_payloads:
            if not p.get('workout_date'):
                p['workout_date'] = canonical_date

        for p in sleep_payloads:
            if not p.get('sleep_end_date'):
                p['sleep_end_date'] = canonical_date

        # Merge cycling workouts
        cycling_result = None
        if cycling_payloads:
            workout_id, merged_data = service.merge_cycling_workout(canonical_date, cycling_payloads)
            cycling_result = merged_data

        # Process sleep data and update readiness
        readiness_results = []
        for sleep_payload in sleep_payloads:
            readiness_date = sleep_payload.get('sleep_end_date') or canonical_date

            # Save sleep summary
            service.save_sleep_summary(
                date=readiness_date,
                sleep_start_time=sleep_payload.get('sleep_start_time'),
                sleep_end_time=sleep_payload.get('sleep_end_time'),
                total_sleep_minutes=sleep_payload.get('total_sleep_minutes'),
                deep_sleep_minutes=sleep_payload.get('deep_sleep_minutes'),
                wakeups_count=sleep_payload.get('wakeups_count'),
                min_heart_rate=sleep_payload.get('min_heart_rate'),
                avg_heart_rate=sleep_payload.get('avg_heart_rate'),
                max_heart_rate=sleep_payload.get('max_heart_rate'),
                notes=sleep_payload.get('notes')
            )

            # Update readiness entry
            readiness = service.update_readiness_from_sleep(readiness_date, sleep_payload)
            if readiness:
                # Convert date for JSON
                if readiness.get('date'):
                    readiness['date'] = readiness['date'].strftime('%Y-%m-%d') if hasattr(readiness['date'], 'strftime') else str(readiness['date'])
                readiness_results.append(readiness)

        return jsonify({
            'success': True,
            'canonical_date': canonical_date,
            'extraction_results': extraction_results,
            'cycling_workout': serialize_for_json(cycling_result),
            'readiness_entries': serialize_for_json(readiness_results),
            'summary': {
                'cycling_images': len(cycling_payloads),
                'sleep_images': len(sleep_payloads),
                'unknown_images': len(unknown_payloads),
                'errors': len([r for r in extraction_results if r.get('type') == 'error'])
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

