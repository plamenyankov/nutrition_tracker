from flask import Blueprint

# Create the main gym blueprint
gym_bp = Blueprint('gym', __name__, url_prefix='/gym')

# Import and register all route modules
from .routes import core, exercises, workouts, templates, progression

# The routes are automatically registered when imported due to the decorators
