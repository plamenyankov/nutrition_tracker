"""
AI Configuration Access Layer

Provides helper functions to load AI profiles (prompts + settings) from the database.
Used by AI Coach and AI Analyzer to get their configuration without hardcoding.

Usage:
    from models.blueprints.cycling_readiness.ai_config import get_prompt_bundle
    
    bundle = get_prompt_bundle("coach")
    system_prompt = bundle["system_prompt"]
    user_template = bundle["user_prompt_template"]
    settings = bundle["settings"]  # dict with model_name, temperature, etc.
"""
import json
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AiProfile:
    """
    Represents an AI profile loaded from the database.
    
    Attributes:
        id: Database primary key
        name: Profile name ("coach" or "analyzer")
        version: Version string (e.g., "v1", "v2_interval_aware")
        is_active: Whether this is the active profile for its name
        system_prompt: The system prompt text
        user_prompt_template: The user prompt template (with {context_json} placeholder)
        settings: Parsed settings dict (model_name, temperature, max_tokens, etc.)
    """
    id: int
    name: str
    version: str
    is_active: bool
    system_prompt: str
    user_prompt_template: Optional[str]
    settings: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'version': self.version,
            'is_active': self.is_active,
            'system_prompt': self.system_prompt,
            'user_prompt_template': self.user_prompt_template,
            'settings': self.settings
        }


class AiProfileNotFoundError(Exception):
    """Raised when no active AI profile is found for a given name."""
    pass


def get_active_profile(name: str, connection_manager=None) -> Optional[AiProfile]:
    """
    Fetch the active AI profile for a given name.
    
    Args:
        name: Profile name ("coach" or "analyzer")
        connection_manager: Optional database connection manager
    
    Returns:
        AiProfile if found and active, None otherwise
    
    Raises:
        Nothing - returns None if not found
    """
    from models.database.connection_manager import get_db_manager
    
    db = connection_manager or get_db_manager()
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute('''
                SELECT id, name, version, is_active, 
                       system_prompt, user_prompt_template, settings_json
                FROM ai_profiles
                WHERE name = %s AND is_active = TRUE
                LIMIT 1
            ''', (name,))
            
            row = cursor.fetchone()
            
            if not row:
                logger.warning(f"[AI_CONFIG] No active profile found for '{name}'")
                return None
            
            # Parse settings_json
            settings = {}
            if row.get('settings_json'):
                try:
                    settings_raw = row['settings_json']
                    if isinstance(settings_raw, str):
                        settings = json.loads(settings_raw)
                    elif isinstance(settings_raw, dict):
                        settings = settings_raw
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"[AI_CONFIG] Failed to parse settings_json for '{name}': {e}")
                    settings = {}
            
            profile = AiProfile(
                id=row['id'],
                name=row['name'],
                version=row['version'],
                is_active=bool(row['is_active']),
                system_prompt=row['system_prompt'],
                user_prompt_template=row.get('user_prompt_template'),
                settings=settings
            )
            
            logger.debug(f"[AI_CONFIG] Loaded profile: {name} {profile.version}")
            return profile
            
    except Exception as e:
        logger.error(f"[AI_CONFIG] Error fetching profile '{name}': {e}")
        return None


def get_prompt_bundle(name: str, connection_manager=None) -> Dict[str, Any]:
    """
    Get a complete prompt bundle for an AI feature.
    
    This is the main function to use when setting up an OpenAI call.
    It returns the system prompt, user template, and parsed settings.
    
    Args:
        name: Profile name ("coach" or "analyzer")
        connection_manager: Optional database connection manager
    
    Returns:
        Dict with keys:
            - system_prompt: str
            - user_prompt_template: str (or None)
            - settings: dict with model_name, temperature, max_tokens, etc.
            - version: str (profile version for logging)
    
    Raises:
        AiProfileNotFoundError: If no active profile exists for the name
    """
    profile = get_active_profile(name, connection_manager)
    
    if not profile:
        raise AiProfileNotFoundError(
            f"AI profile '{name}' not configured. "
            f"Ensure the ai_profiles table has an active row with name='{name}'."
        )
    
    return {
        'system_prompt': profile.system_prompt,
        'user_prompt_template': profile.user_prompt_template,
        'settings': profile.settings,
        'version': profile.version
    }


def get_profile_setting(name: str, key: str, default: Any = None, connection_manager=None) -> Any:
    """
    Get a specific setting from an AI profile.
    
    Convenience function to fetch a single setting value.
    
    Args:
        name: Profile name ("coach" or "analyzer")
        key: Setting key (e.g., "model_name", "temperature", "history_days")
        default: Default value if key not found
        connection_manager: Optional database connection manager
    
    Returns:
        The setting value, or default if not found
    """
    try:
        bundle = get_prompt_bundle(name, connection_manager)
        return bundle['settings'].get(key, default)
    except AiProfileNotFoundError:
        logger.warning(f"[AI_CONFIG] Profile '{name}' not found, returning default for '{key}'")
        return default


def list_profiles(connection_manager=None) -> list:
    """
    List all AI profiles in the database.
    
    Useful for admin/debugging purposes.
    
    Returns:
        List of dicts with profile info (id, name, version, is_active)
    """
    from models.database.connection_manager import get_db_manager
    
    db = connection_manager or get_db_manager()
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute('''
                SELECT id, name, version, is_active, 
                       LENGTH(system_prompt) as prompt_length,
                       created_at, updated_at
                FROM ai_profiles
                ORDER BY name, version
            ''')
            
            return cursor.fetchall()
            
    except Exception as e:
        logger.error(f"[AI_CONFIG] Error listing profiles: {e}")
        return []

