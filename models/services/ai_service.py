from models import openai_utils
from models.food import FoodDatabase
import pandas as pd
import io
from datetime import datetime
from flask import session
import uuid

class AIService:
    def __init__(self):
        self.food_db = FoodDatabase()

    def _get_session_key(self):
        """Get a unique session key for storing results"""
        if 'ai_session_id' not in session:
            session['ai_session_id'] = str(uuid.uuid4())
        return f"ai_results_{session['ai_session_id']}"

    def _store_results(self, results_df):
        """Store results in session"""
        session_key = self._get_session_key()
        # Store as CSV string in session
        session[session_key] = results_df.to_csv(index=False)
        session.permanent = True

    def _get_stored_results(self):
        """Get stored results from session"""
        session_key = self._get_session_key()
        if session_key in session:
            try:
                data_io = io.StringIO(session[session_key])
                return pd.read_csv(data_io)
            except:
                return None
        return None

    def _clear_stored_results(self):
        """Clear stored results from session"""
        session_key = self._get_session_key()
        if session_key in session:
            session.pop(session_key, None)

    def analyze_foods(self, user_input):
        """Analyze foods using OpenAI (text-based)"""
        # Clear any previous results first
        self._clear_stored_results()

        try:
            # Get OpenAI response
            response = openai_utils.get_openai_response(user_input)

            # Parse CSV response
            data_io = io.StringIO(response)
            temp_results = pd.read_csv(data_io)

            # Store results in session
            self._store_results(temp_results)

            # Convert results for display
            results = temp_results.to_dict(orient='records')
            columns = temp_results.columns.tolist()

            return {
                'success': True,
                'results': results,
                'columns': columns
            }

        except Exception as e:
            # Clear any partial results on error
            self._clear_stored_results()
            return {
                'success': False,
                'error': f'Error analyzing foods: {str(e)}'
            }

    def analyze_meal_photo(self, base64_image):
        """Analyze meal photo using OpenAI Vision"""
        # Clear any previous results first
        self._clear_stored_results()

        try:
            # Get OpenAI response for meal photo
            response = openai_utils.analyze_meal_image(base64_image)

            # Parse CSV response
            data_io = io.StringIO(response)
            temp_results = pd.read_csv(data_io)

            # Store results in session
            self._store_results(temp_results)

            # Convert results for display
            results = temp_results.to_dict(orient='records')
            columns = temp_results.columns.tolist()

            return {
                'success': True,
                'results': results,
                'columns': columns
            }

        except Exception as e:
            # Clear any partial results on error
            self._clear_stored_results()
            return {
                'success': False,
                'error': f'Error analyzing meal photo: {str(e)}'
            }

    def analyze_nutrition_label(self, base64_image, food_name):
        """Analyze nutrition label with provided food name"""
        # Clear any previous results first
        self._clear_stored_results()

        try:
            # Get OpenAI response for nutrition label
            response = openai_utils.analyze_nutrition_label(base64_image, food_name)

            # Parse CSV response
            data_io = io.StringIO(response)
            temp_results = pd.read_csv(data_io)

            # Store results in session
            self._store_results(temp_results)

            # Convert results for display
            results = temp_results.to_dict(orient='records')
            columns = temp_results.columns.tolist()

            return {
                'success': True,
                'results': results,
                'columns': columns
            }

        except Exception as e:
            # Clear any partial results on error
            self._clear_stored_results()
            return {
                'success': False,
                'error': f'Error analyzing nutrition label: {str(e)}'
            }

    def analyze_product_photos(self, nutrition_base64, front_base64):
        """Analyze product using nutrition label and front photos"""
        # Clear any previous results first
        self._clear_stored_results()

        try:
            # Get OpenAI response for product photos
            response = openai_utils.analyze_product_images(nutrition_base64, front_base64)

            # Parse CSV response
            data_io = io.StringIO(response)
            temp_results = pd.read_csv(data_io)

            # Store results in session
            self._store_results(temp_results)

            # Convert results for display
            results = temp_results.to_dict(orient='records')
            columns = temp_results.columns.tolist()

            return {
                'success': True,
                'results': results,
                'columns': columns
            }

        except Exception as e:
            # Clear any partial results on error
            self._clear_stored_results()
            return {
                'success': False,
                'error': f'Error analyzing product photos: {str(e)}'
            }

    def save_analysis_results(self):
        """Save analyzed foods to database"""
        temp_results = self._get_stored_results()

        if temp_results is not None:
            try:
                # Clean column names
                temp_results.columns = temp_results.columns.str.strip()

                # Save to database
                self.food_db.save_to_database(temp_results.to_csv(index=False))

                # Clear stored results after successful save
                self._clear_stored_results()

                return {
                    'success': True,
                    'message': 'Foods saved to database successfully!'
                }

            except Exception as e:
                # Don't clear results on save error - user might want to retry
                return {
                    'success': False,
                    'error': f'Error saving foods: {str(e)}'
                }
        else:
            return {
                'success': False,
                'error': 'No analysis results to save. Please analyze foods first.'
            }

    def create_recipe_from_results(self, recipe_name, servings, included_indices):
        """Create a recipe from the temporary results"""
        temp_results = self._get_stored_results()

        if temp_results is None:
            return {
                'success': False,
                'error': 'No analysis results available to create recipe. Please analyze foods first.'
            }

        try:
            # Filter results based on selected indices
            included_indices = [int(idx) for idx in included_indices]
            selected_results = temp_results.iloc[included_indices]

            if selected_results.empty:
                return {
                    'success': False,
                    'error': 'No ingredients selected for the recipe'
                }

            # Save ingredients to database first (to get IDs)
            csv_data = selected_results.to_csv(index=False)

            # Save recipe
            date = datetime.now().strftime('%Y-%m-%d')
            result = self.food_db.save_recipe(date, recipe_name, servings, csv_data)

            if isinstance(result, list):
                # Clear results after successful recipe creation
                self._clear_stored_results()
                return {
                    'success': True,
                    'message': f'Recipe "{recipe_name}" created successfully!'
                }
            else:
                return {
                    'success': False,
                    'error': f'Error creating recipe: {result}'
                }

        except Exception as e:
            return {
                'success': False,
                'error': f'Error creating recipe: {str(e)}'
            }
