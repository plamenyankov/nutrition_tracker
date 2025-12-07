"""
Cycling & Readiness Blueprint
Handles cycling workouts and morning readiness tracking with AI-powered image extraction.
"""
from flask import Blueprint

# Create the cycling_readiness blueprint
cycling_readiness_bp = Blueprint(
    'cycling_readiness',
    __name__,
    url_prefix='/cycling-readiness'
)

# Import routes package to register all route modules
from . import routes  # noqa: F401
