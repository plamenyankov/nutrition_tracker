"""
AI Lab routes for Cycling Readiness feature.
Provides UI and API for managing AI profiles (prompts + settings).
"""
import json
from flask import render_template, request, jsonify
from flask_login import login_required

from .. import cycling_readiness_bp
from ..ai_config import get_active_profile, list_profiles, AiProfile
from .helpers import (
    logger,
    serialize_for_json,
    get_base_context,
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

