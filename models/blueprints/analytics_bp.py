from flask import Blueprint, render_template
from flask_login import login_required

analytics_bp = Blueprint('analytics_bp', __name__, url_prefix='/analytics')

@analytics_bp.route('')
@login_required
def analytics():
    """Analytics - View nutrition trends and insights"""
    return render_template('nutrition_app/analytics.html')
