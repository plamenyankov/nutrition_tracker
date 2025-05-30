from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from models.services.ai_service import AIService

ai_bp = Blueprint('ai_bp', __name__, url_prefix='/ai')
ai_service = AIService()

@ai_bp.route('/assistant', methods=['GET', 'POST'])
@login_required
def ai_assistant():
    """AI Assistant - OpenAI nutrition analysis"""
    if request.method == 'POST':
        user_input = request.form.get('foods', '')
        if user_input:
            result = ai_service.analyze_foods(user_input)

            if result['success']:
                flash('Analysis complete! Review the results below.', 'success')
                return render_template('nutrition_app/ai_assistant.html',
                                     results=result['results'],
                                     columns=result['columns'])
            else:
                flash(result['error'], 'danger')
                return render_template('nutrition_app/ai_assistant.html')

    return render_template('nutrition_app/ai_assistant.html')

@ai_bp.route('/save-results', methods=['POST'])
@login_required
def save_ai_results():
    """Save AI analysis results to food database"""
    result = ai_service.save_analysis_results()

    if result['success']:
        flash(result['message'], 'success')
    else:
        flash(result['error'], 'danger')

    return redirect(url_for('ai_bp.ai_assistant'))
