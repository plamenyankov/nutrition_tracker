from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from models.services.ai_service import AIService
import base64
from werkzeug.exceptions import RequestEntityTooLarge

ai_bp = Blueprint('ai_bp', __name__, url_prefix='/ai')
ai_service = AIService()

@ai_bp.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    flash('File size too large. Images are automatically compressed, but if you still see this error, please try a smaller image.', 'danger')
    return redirect(url_for('ai_bp.ai_assistant'))

@ai_bp.route('/assistant', methods=['GET', 'POST'])
@login_required
def ai_assistant():
    """AI Assistant - OpenAI nutrition analysis"""
    if request.method == 'POST':
        analysis_method = request.form.get('analysis_method', 'text')

        try:
            result = None

            if analysis_method == 'text':
                # Original text-based analysis
                user_input = request.form.get('foods', '')
                if user_input:
                    result = ai_service.analyze_foods(user_input)
                else:
                    flash('Please enter foods to analyze.', 'warning')
                    return render_template('nutrition_app/ai_assistant.html')

            elif analysis_method == 'meal_photo':
                # Analyze meal photo
                if 'meal_photo' in request.files:
                    photo = request.files['meal_photo']
                    if photo and photo.filename:
                        # Read and encode image
                        image_data = photo.read()
                        base64_image = base64.b64encode(image_data).decode('utf-8')
                        result = ai_service.analyze_meal_photo(base64_image)
                    else:
                        flash('Please upload a meal photo.', 'warning')
                        return render_template('nutrition_app/ai_assistant.html')
                else:
                    flash('Please upload a meal photo.', 'warning')
                    return render_template('nutrition_app/ai_assistant.html')

            elif analysis_method == 'label_manual':
                # Analyze nutrition label with manual food name
                food_name = request.form.get('food_name', '')
                if 'label_photo' in request.files and food_name:
                    photo = request.files['label_photo']
                    if photo and photo.filename:
                        # Read and encode image
                        image_data = photo.read()
                        base64_image = base64.b64encode(image_data).decode('utf-8')
                        result = ai_service.analyze_nutrition_label(base64_image, food_name)
                    else:
                        flash('Please upload a nutrition label photo.', 'warning')
                        return render_template('nutrition_app/ai_assistant.html')
                else:
                    flash('Please upload a nutrition label photo and enter the food name.', 'warning')
                    return render_template('nutrition_app/ai_assistant.html')

            elif analysis_method == 'label_auto':
                # Analyze nutrition label and product front photos
                if 'nutrition_photo' in request.files and 'front_photo' in request.files:
                    nutrition_photo = request.files['nutrition_photo']
                    front_photo = request.files['front_photo']

                    if nutrition_photo and nutrition_photo.filename and front_photo and front_photo.filename:
                        # Read and encode images
                        nutrition_data = nutrition_photo.read()
                        nutrition_base64 = base64.b64encode(nutrition_data).decode('utf-8')

                        front_data = front_photo.read()
                        front_base64 = base64.b64encode(front_data).decode('utf-8')

                        result = ai_service.analyze_product_photos(nutrition_base64, front_base64)
                    else:
                        flash('Please upload both nutrition label and product front photos.', 'warning')
                        return render_template('nutrition_app/ai_assistant.html')
                else:
                    flash('Please upload both nutrition label and product front photos.', 'warning')
                    return render_template('nutrition_app/ai_assistant.html')

            # Process result
            if result and result['success']:
                flash('Analysis complete! Review the results below.', 'success')
                return render_template('nutrition_app/ai_assistant.html',
                                     results=result['results'],
                                     columns=result['columns'])
            elif result:
                flash(result['error'], 'danger')
                return render_template('nutrition_app/ai_assistant.html')

        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'danger')
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
