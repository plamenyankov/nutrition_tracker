"""
AI Lab routes for Cycling Readiness feature.
Provides UI and API for managing AI profiles (prompts + settings).
Also provides Playground/Debug endpoints for testing prompts without persisting.
"""
import json
from datetime import datetime, date
from flask import render_template, request, jsonify
from flask_login import login_required, current_user

from .. import cycling_readiness_bp
from ..ai_config import get_active_profile, list_profiles, get_profile_by_id, AiProfile
from .helpers import (
    logger,
    serialize_for_json,
    get_base_context,
    get_service,
)


# ============== Page Route ==============

@cycling_readiness_bp.route('/ai-lab')
@login_required
def ai_lab_page():
    """
    AI Lab page - Manage AI Coach and AI Analyzer prompts and settings.
    
    TODO: Add admin-only check if current_user.is_admin exists
    """
    from models.database.connection_manager import get_db_manager
    
    context = get_base_context()
    context['current_tab'] = 'ai_lab'
    
    # Fetch all profiles grouped by name
    db = get_db_manager()
    profiles_by_name = {'coach': [], 'analyzer': []}
    active_profiles = {'coach': None, 'analyzer': None}
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            
            # Fetch all profiles
            cursor.execute('''
                SELECT id, name, version, is_active, 
                       system_prompt, user_prompt_template, settings_json,
                       created_at, updated_at
                FROM ai_profiles
                ORDER BY name, created_at DESC
            ''')
            
            for row in cursor.fetchall():
                profile_dict = {
                    'id': row['id'],
                    'name': row['name'],
                    'version': row['version'],
                    'is_active': bool(row['is_active']),
                    'system_prompt': row['system_prompt'],
                    'user_prompt_template': row.get('user_prompt_template') or '',
                    'settings_json': row.get('settings_json') or '{}',
                    'created_at': row['created_at'].strftime('%Y-%m-%d %H:%M') if row.get('created_at') else '',
                    'updated_at': row['updated_at'].strftime('%Y-%m-%d %H:%M') if row.get('updated_at') else ''
                }
                
                name = row['name']
                if name in profiles_by_name:
                    profiles_by_name[name].append(profile_dict)
                    if row['is_active']:
                        active_profiles[name] = profile_dict
                        
    except Exception as e:
        logger.error(f"[AI_LAB] Error loading profiles: {e}")
    
    context['profiles'] = profiles_by_name
    context['active_profiles'] = active_profiles
    context['today_date'] = date.today().strftime('%Y-%m-%d')
    
    return render_template('cycling_readiness/ai_lab.html', **context)


# ============== API Routes ==============

@cycling_readiness_bp.route('/api/ai-profiles', methods=['GET'])
@login_required
def api_list_profiles():
    """List all AI profiles."""
    profiles = list_profiles()
    return jsonify({
        'success': True,
        'profiles': serialize_for_json(profiles)
    })


@cycling_readiness_bp.route('/api/ai-profiles/<int:profile_id>', methods=['GET'])
@login_required
def api_get_profile(profile_id):
    """Get a single AI profile by ID."""
    from models.database.connection_manager import get_db_manager
    
    db = get_db_manager()
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute('''
                SELECT id, name, version, is_active, 
                       system_prompt, user_prompt_template, settings_json,
                       created_at, updated_at
                FROM ai_profiles
                WHERE id = %s
            ''', (profile_id,))
            
            row = cursor.fetchone()
            
            if not row:
                return jsonify({'success': False, 'error': 'Profile not found'}), 404
            
            profile = {
                'id': row['id'],
                'name': row['name'],
                'version': row['version'],
                'is_active': bool(row['is_active']),
                'system_prompt': row['system_prompt'],
                'user_prompt_template': row.get('user_prompt_template') or '',
                'settings_json': row.get('settings_json') or '{}',
                'created_at': row['created_at'].isoformat() if row.get('created_at') else None,
                'updated_at': row['updated_at'].isoformat() if row.get('updated_at') else None
            }
            
            return jsonify({'success': True, 'profile': profile})
            
    except Exception as e:
        logger.error(f"[AI_LAB] Error fetching profile {profile_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@cycling_readiness_bp.route('/api/ai-profiles/<int:profile_id>/update', methods=['POST'])
@login_required
def api_update_profile(profile_id):
    """
    Update an AI profile.
    
    Payload: {version, system_prompt, user_prompt_template, settings_json}
    """
    from models.database.connection_manager import get_db_manager
    
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    # Validate version
    version = data.get('version', '').strip()
    if not version:
        return jsonify({'success': False, 'error': 'Version is required'}), 400
    
    # Validate settings_json is valid JSON
    settings_json = data.get('settings_json', '{}')
    try:
        json.loads(settings_json)
    except json.JSONDecodeError as e:
        return jsonify({'success': False, 'error': f'Invalid settings JSON: {str(e)}'}), 400
    
    system_prompt = data.get('system_prompt', '')
    user_prompt_template = data.get('user_prompt_template', '')
    
    db = get_db_manager()
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check profile exists
            cursor.execute('SELECT id FROM ai_profiles WHERE id = %s', (profile_id,))
            if not cursor.fetchone():
                return jsonify({'success': False, 'error': 'Profile not found'}), 404
            
            # Update profile
            cursor.execute('''
                UPDATE ai_profiles 
                SET version = %s, 
                    system_prompt = %s, 
                    user_prompt_template = %s, 
                    settings_json = %s,
                    updated_at = NOW()
                WHERE id = %s
            ''', (version, system_prompt, user_prompt_template, settings_json, profile_id))
            
            conn.commit()
            
            logger.info(f"[AI_LAB] Updated profile {profile_id}, version={version}")
            
            return jsonify({'success': True, 'message': 'Profile updated successfully'})
            
    except Exception as e:
        logger.error(f"[AI_LAB] Error updating profile {profile_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@cycling_readiness_bp.route('/api/ai-profiles/<int:profile_id>/duplicate', methods=['POST'])
@login_required
def api_duplicate_profile(profile_id):
    """
    Duplicate an AI profile.
    
    Creates a new profile with:
    - Same name as original
    - Version = original.version + "_copy"
    - is_active = false
    - Copies all text fields
    """
    from models.database.connection_manager import get_db_manager
    
    db = get_db_manager()
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            
            # Fetch original profile
            cursor.execute('''
                SELECT name, version, system_prompt, user_prompt_template, settings_json
                FROM ai_profiles
                WHERE id = %s
            ''', (profile_id,))
            
            original = cursor.fetchone()
            if not original:
                return jsonify({'success': False, 'error': 'Profile not found'}), 404
            
            # Generate new version name
            new_version = f"{original['version']}_copy"
            
            # Check if this version already exists
            cursor.execute('''
                SELECT id FROM ai_profiles 
                WHERE name = %s AND version = %s
            ''', (original['name'], new_version))
            
            if cursor.fetchone():
                # Add suffix to make unique
                import time
                new_version = f"{original['version']}_copy_{int(time.time()) % 10000}"
            
            # Create new profile
            cursor.execute('''
                INSERT INTO ai_profiles 
                    (name, version, is_active, system_prompt, user_prompt_template, settings_json)
                VALUES 
                    (%s, %s, FALSE, %s, %s, %s)
            ''', (
                original['name'],
                new_version,
                original['system_prompt'],
                original.get('user_prompt_template') or '',
                original.get('settings_json') or '{}'
            ))
            
            new_id = cursor.lastrowid
            conn.commit()
            
            logger.info(f"[AI_LAB] Duplicated profile {profile_id} -> {new_id}, version={new_version}")
            
            return jsonify({
                'success': True, 
                'new_id': new_id,
                'new_version': new_version,
                'message': f'Profile duplicated as "{new_version}"'
            })
            
    except Exception as e:
        logger.error(f"[AI_LAB] Error duplicating profile {profile_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@cycling_readiness_bp.route('/api/ai-profiles/<int:profile_id>/set-active', methods=['POST'])
@login_required
def api_set_active_profile(profile_id):
    """
    Set a profile as active.
    
    - Sets this profile to is_active = true
    - Sets all other profiles with the same name to is_active = false
    """
    from models.database.connection_manager import get_db_manager
    
    db = get_db_manager()
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            
            # Get the profile's name
            cursor.execute('SELECT name, version FROM ai_profiles WHERE id = %s', (profile_id,))
            profile = cursor.fetchone()
            
            if not profile:
                return jsonify({'success': False, 'error': 'Profile not found'}), 404
            
            name = profile['name']
            
            # Deactivate all profiles with this name
            cursor.execute('''
                UPDATE ai_profiles 
                SET is_active = FALSE, updated_at = NOW()
                WHERE name = %s
            ''', (name,))
            
            # Activate the selected profile
            cursor.execute('''
                UPDATE ai_profiles 
                SET is_active = TRUE, updated_at = NOW()
                WHERE id = %s
            ''', (profile_id,))
            
            conn.commit()
            
            logger.info(f"[AI_LAB] Set profile {profile_id} ({name} {profile['version']}) as active")
            
            return jsonify({
                'success': True, 
                'message': f'Profile "{profile["version"]}" is now active for {name}'
            })
            
    except Exception as e:
        logger.error(f"[AI_LAB] Error setting active profile {profile_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============== Playground / Debug API Routes ==============

@cycling_readiness_bp.route('/api/ai-lab/coach/payload', methods=['GET'])
@login_required
def api_coach_payload():
    """
    Preview the payload that would be sent to OpenAI for AI Coach.
    
    Query params:
        - date: ISO date string (YYYY-MM-DD), defaults to today
        - profile_id: Optional profile ID to use (uses active if omitted)
    
    Returns:
        JSON with tool, profile info, and the complete payload
    """
    from models.services.training_recommendation import build_coach_payload
    
    # Parse date parameter
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
        target_date = date.today()
    
    # Parse profile_id parameter
    profile_id = request.args.get('profile_id', type=int)
    profile_dict = None
    profile_info = {'using_active': True, 'id': None, 'version': None}
    
    if profile_id:
        profile = get_profile_by_id(profile_id)
        if not profile:
            return jsonify({
                'success': False,
                'error': f'Profile {profile_id} not found'
            }), 404
        if profile.name != 'coach':
            return jsonify({
                'success': False,
                'error': f'Profile {profile_id} is not a coach profile'
            }), 400
        profile_dict = profile.to_dict()
        profile_info = {
            'using_active': False,
            'id': profile.id,
            'version': profile.version
        }
    else:
        # Get active profile info for display
        active = get_active_profile('coach')
        if active:
            profile_info = {
                'using_active': True,
                'id': active.id,
                'version': active.version
            }
    
    try:
        payload = build_coach_payload(
            target_date=target_date,
            user_id=current_user.id,
            profile=profile_dict
        )
        
        return jsonify({
            'success': True,
            'tool': 'coach',
            'date': target_date.strftime('%Y-%m-%d'),
            'profile': profile_info,
            'payload': serialize_for_json(payload)
        })
        
    except Exception as e:
        logger.error(f"[AI_LAB] Error building coach payload: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@cycling_readiness_bp.route('/api/ai-lab/coach/dry-run', methods=['POST'])
@login_required
def api_coach_dry_run():
    """
    Execute a dry-run of AI Coach: call OpenAI and return the result
    WITHOUT saving anything to the database.
    
    Body:
        {
            "date": "YYYY-MM-DD",
            "profile_id": <optional int>
        }
    
    Returns:
        JSON with payload, raw_response, parsed_result, profile_version, tool_name
    """
    from models.services.training_recommendation import run_coach_dry_run
    
    data = request.get_json() or {}
    
    # Parse date parameter
    date_str = data.get('date')
    if date_str:
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid date format. Use YYYY-MM-DD.'
            }), 400
    else:
        target_date = date.today()
    
    # Parse profile_id parameter
    profile_id = data.get('profile_id')
    profile_dict = None
    
    if profile_id:
        try:
            profile_id = int(profile_id)
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'error': 'profile_id must be an integer'
            }), 400
            
        profile = get_profile_by_id(profile_id)
        if not profile:
            return jsonify({
                'success': False,
                'error': f'Profile {profile_id} not found'
            }), 404
        if profile.name != 'coach':
            return jsonify({
                'success': False,
                'error': f'Profile {profile_id} is not a coach profile'
            }), 400
        profile_dict = profile.to_dict()
    
    try:
        result = run_coach_dry_run(
            target_date=target_date,
            user_id=current_user.id,
            profile=profile_dict
        )
        
        return jsonify({
            'success': True,
            'date': target_date.strftime('%Y-%m-%d'),
            **serialize_for_json(result)
        })
        
    except Exception as e:
        logger.error(f"[AI_LAB] Error in coach dry-run: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@cycling_readiness_bp.route('/api/ai-lab/analyzer/payload', methods=['GET'])
@login_required
def api_analyzer_payload():
    """
    Preview the payload that would be sent to OpenAI for AI Analyzer.
    
    Query params:
        - workout_id: Required workout ID to analyze
        - profile_id: Optional profile ID to use (uses active if omitted)
    
    Returns:
        JSON with tool, profile info, and the complete payload
    """
    from models.services.ai_analyzer_service import build_analyzer_payload
    
    # Parse workout_id parameter (required)
    workout_id = request.args.get('workout_id', type=int)
    if not workout_id:
        return jsonify({
            'success': False,
            'error': 'workout_id is required'
        }), 400
    
    # Parse profile_id parameter
    profile_id = request.args.get('profile_id', type=int)
    profile_dict = None
    profile_info = {'using_active': True, 'id': None, 'version': None}
    
    if profile_id:
        profile = get_profile_by_id(profile_id)
        if not profile:
            return jsonify({
                'success': False,
                'error': f'Profile {profile_id} not found'
            }), 404
        if profile.name != 'analyzer':
            return jsonify({
                'success': False,
                'error': f'Profile {profile_id} is not an analyzer profile'
            }), 400
        profile_dict = profile.to_dict()
        profile_info = {
            'using_active': False,
            'id': profile.id,
            'version': profile.version
        }
    else:
        # Get active profile info for display
        active = get_active_profile('analyzer')
        if active:
            profile_info = {
                'using_active': True,
                'id': active.id,
                'version': active.version
            }
    
    try:
        payload = build_analyzer_payload(
            workout_id=workout_id,
            user_id=current_user.id,
            profile=profile_dict
        )
        
        return jsonify({
            'success': True,
            'tool': 'analyzer',
            'workout_id': workout_id,
            'profile': profile_info,
            'payload': serialize_for_json(payload)
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404
    except Exception as e:
        logger.error(f"[AI_LAB] Error building analyzer payload: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@cycling_readiness_bp.route('/api/ai-lab/analyzer/dry-run', methods=['POST'])
@login_required
def api_analyzer_dry_run():
    """
    Execute a dry-run of AI Analyzer: call OpenAI and return the result
    WITHOUT saving anything to the database.
    
    Body:
        {
            "workout_id": <int>,
            "profile_id": <optional int>
        }
    
    Returns:
        JSON with payload, raw_response, parsed_result, profile_version, tool_name
    """
    from models.services.ai_analyzer_service import run_analyzer_dry_run
    
    data = request.get_json() or {}
    
    # Parse workout_id parameter (required)
    workout_id = data.get('workout_id')
    if not workout_id:
        return jsonify({
            'success': False,
            'error': 'workout_id is required'
        }), 400
    
    try:
        workout_id = int(workout_id)
    except (ValueError, TypeError):
        return jsonify({
            'success': False,
            'error': 'workout_id must be an integer'
        }), 400
    
    # Parse profile_id parameter
    profile_id = data.get('profile_id')
    profile_dict = None
    
    if profile_id:
        try:
            profile_id = int(profile_id)
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'error': 'profile_id must be an integer'
            }), 400
            
        profile = get_profile_by_id(profile_id)
        if not profile:
            return jsonify({
                'success': False,
                'error': f'Profile {profile_id} not found'
            }), 404
        if profile.name != 'analyzer':
            return jsonify({
                'success': False,
                'error': f'Profile {profile_id} is not an analyzer profile'
            }), 400
        profile_dict = profile.to_dict()
    
    try:
        result = run_analyzer_dry_run(
            workout_id=workout_id,
            user_id=current_user.id,
            profile=profile_dict
        )
        
        return jsonify({
            'success': True,
            'workout_id': workout_id,
            **serialize_for_json(result)
        })
        
    except Exception as e:
        logger.error(f"[AI_LAB] Error in analyzer dry-run: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@cycling_readiness_bp.route('/api/ai-lab/workouts', methods=['GET'])
@login_required
def api_get_recent_workouts():
    """
    Get recent workouts for the Playground workout selector.
    
    Query params:
        - limit: Number of workouts to return (default 20)
    
    Returns:
        JSON with list of recent workouts
    """
    limit = request.args.get('limit', 20, type=int)
    
    try:
        service = get_service()
        workouts = service.get_cycling_workouts(limit=limit)
        
        # Simplify workout data for dropdown
        workout_list = []
        for w in workouts:
            duration_min = int(w.get('duration_sec', 0) / 60) if w.get('duration_sec') else None
            workout_list.append({
                'id': w.get('id'),
                'date': w.get('date').strftime('%Y-%m-%d') if hasattr(w.get('date'), 'strftime') else str(w.get('date')),
                'duration_min': duration_min,
                'avg_power_w': w.get('avg_power_w'),
                'avg_hr_bpm': w.get('avg_heart_rate'),
                'tss': w.get('tss'),
                'source': w.get('source')
            })
        
        return jsonify({
            'success': True,
            'workouts': workout_list
        })
        
    except Exception as e:
        logger.error(f"[AI_LAB] Error fetching workouts: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

