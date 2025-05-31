from models import openai_utils
from models.food import FoodDatabase
import pandas as pd
import io

class AIService:
    def __init__(self):
        self.food_db = FoodDatabase()
        self.temp_results = None

    def analyze_foods(self, user_input):
        """Analyze foods using OpenAI (text-based)"""
        try:
            # Get OpenAI response
            response = openai_utils.get_openai_response(user_input)

            # Parse CSV response
            data_io = io.StringIO(response)
            self.temp_results = pd.read_csv(data_io)

            # Convert results for display
            results = self.temp_results.to_dict(orient='records')
            columns = self.temp_results.columns.tolist()

            return {
                'success': True,
                'results': results,
                'columns': columns
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Error analyzing foods: {str(e)}'
            }

    def analyze_meal_photo(self, base64_image):
        """Analyze meal photo using OpenAI Vision"""
        try:
            # Get OpenAI response for meal photo
            response = openai_utils.analyze_meal_image(base64_image)

            # Parse CSV response
            data_io = io.StringIO(response)
            self.temp_results = pd.read_csv(data_io)

            # Convert results for display
            results = self.temp_results.to_dict(orient='records')
            columns = self.temp_results.columns.tolist()

            return {
                'success': True,
                'results': results,
                'columns': columns
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Error analyzing meal photo: {str(e)}'
            }

    def analyze_nutrition_label(self, base64_image, food_name):
        """Analyze nutrition label with provided food name"""
        try:
            # Get OpenAI response for nutrition label
            response = openai_utils.analyze_nutrition_label(base64_image, food_name)

            # Parse CSV response
            data_io = io.StringIO(response)
            self.temp_results = pd.read_csv(data_io)

            # Convert results for display
            results = self.temp_results.to_dict(orient='records')
            columns = self.temp_results.columns.tolist()

            return {
                'success': True,
                'results': results,
                'columns': columns
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Error analyzing nutrition label: {str(e)}'
            }

    def analyze_product_photos(self, nutrition_base64, front_base64):
        """Analyze product using nutrition label and front photos"""
        try:
            # Get OpenAI response for product photos
            response = openai_utils.analyze_product_images(nutrition_base64, front_base64)

            # Parse CSV response
            data_io = io.StringIO(response)
            self.temp_results = pd.read_csv(data_io)

            # Convert results for display
            results = self.temp_results.to_dict(orient='records')
            columns = self.temp_results.columns.tolist()

            return {
                'success': True,
                'results': results,
                'columns': columns
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Error analyzing product photos: {str(e)}'
            }

    def save_analysis_results(self):
        """Save analyzed foods to database"""
        if self.temp_results is not None:
            try:
                # Clean column names
                self.temp_results.columns = self.temp_results.columns.str.strip()

                # Save to database
                self.food_db.save_to_database(self.temp_results.to_csv(index=False))

                # Clear temporary results
                self.temp_results = None

                return {
                    'success': True,
                    'message': 'Foods saved to database successfully!'
                }

            except Exception as e:
                return {
                    'success': False,
                    'error': f'Error saving foods: {str(e)}'
                }
        else:
            return {
                'success': False,
                'error': 'No analysis results to save'
            }
