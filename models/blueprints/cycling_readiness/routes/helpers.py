"""
Shared helpers for Cycling Readiness routes.
Contains utility functions, constants, and common imports used across route modules.
"""
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from flask_login import current_user

from models.services.cycling_readiness_service import CyclingReadinessService

logger = logging.getLogger(__name__)


# ============== JSON Serialization ==============

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


# ============== Missing Fields Detection ==============

# Fields that should never be zero (0 is as bad as null for these)
CYCLING_NUMERIC_FIELDS = [
    'duration_sec', 'distance_km', 'avg_power_w', 'max_power_w', 
    'normalized_power_w', 'tss', 'intensity_factor', 'avg_heart_rate', 
    'max_heart_rate', 'avg_cadence', 'kcal_active', 'kcal_total'
]

SLEEP_NUMERIC_FIELDS = [
    'total_sleep_minutes', 'deep_sleep_minutes', 'awake_minutes',
    'min_heart_rate', 'max_heart_rate'
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


# ============== Service Access ==============

def get_service():
    """Get CyclingReadinessService instance for current user"""
    user_id = current_user.id if current_user.is_authenticated else None
    return CyclingReadinessService(user_id=user_id)


# ============== Page Context ==============

def get_base_context():
    """Get common context data for all pages."""
    service = get_service()
    cycling_stats = service.get_cycling_stats(days=30)
    return {
        'cycling_stats': cycling_stats,
        'today': datetime.now().strftime('%Y-%m-%d')
    }



