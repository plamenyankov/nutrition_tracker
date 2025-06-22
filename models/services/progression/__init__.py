"""
Progression Service Module
Export the main ProgressionService class
"""

from .services.progression_service import ProgressionService

# For backward compatibility, also export from the old location
try:
    from ..progression_service import ProgressionService as LegacyProgressionService
except ImportError:
    LegacyProgressionService = None

__all__ = ['ProgressionService']
