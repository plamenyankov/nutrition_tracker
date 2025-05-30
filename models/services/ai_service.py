from models import openai_utils
from models.food import FoodDatabase
import pandas as pd
import io

class AIService:
    def __init__(self):
        self.food_db = FoodDatabase()
        self.temp_results = None

    def analyze_foods(self, user_input):
        """Analyze foods using OpenAI"""
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
