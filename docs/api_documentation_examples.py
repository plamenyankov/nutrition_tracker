"""
Example Swagger documentation for key endpoints
"""

# Food Database API Documentation Examples:

@food_bp.route('/api/paginated')
def get_foods_paginated():
    """
    Get paginated food list
    ---
    tags:
      - Food Database
    parameters:
      - name: page
        in: query
        type: integer
        default: 1
        description: Page number
      - name: per_page
        in: query
        type: integer
        default: 20
        description: Items per page
      - name: search
        in: query
        type: string
        description: Search term for food names
    responses:
      200:
        description: Paginated food list
        schema:
          type: object
          properties:
            foods:
              type: array
              items:
                type: object
                properties:
                  ingredient_id:
                    type: integer
                  name:
                    type: string
                  kcal:
                    type: number
                  protein:
                    type: number
                  carb:
                    type: number
                  fat:
                    type: number
            pagination:
              type: object
              properties:
                page:
                  type: integer
                per_page:
                  type: integer
                total:
                  type: integer
                pages:
                  type: integer
    """

# Gym API Documentation Examples:

@gym_bp.route('/exercise/<int:exercise_id>/set-specific-progression/<int:set_number>')
def get_set_specific_progression(exercise_id, set_number):
    """
    Get progression suggestion for specific set
    ---
    tags:
      - Progression
    parameters:
      - name: exercise_id
        in: path
        type: integer
        required: true
        description: Exercise ID
      - name: set_number
        in: path
        type: integer
        required: true
        description: Set number (1, 2, 3, etc.)
    responses:
      200:
        description: Set-specific progression data
        schema:
          type: object
          properties:
            has_history:
              type: boolean
            set_number:
              type: integer
            current_weight:
              type: number
            suggested_weight:
              type: number
            suggested_reps:
              type: integer
            suggestion:
              type: string
              enum: [increase_weight, build_strength, build_reps, maintain]
            ready:
              type: boolean
            confidence:
              type: number
            reps_to_go:
              type: integer
            target_reps:
              type: integer
    """

# Timer API Documentation Examples:

@timer_bp.route('/api/timer/workout/start', methods=['POST'])
def start_workout_timer():
    """
    Start workout timer
    ---
    tags:
      - Timer
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            session_id:
              type: integer
              description: Workout session ID
            notes:
              type: string
              description: Optional workout notes
    responses:
      200:
        description: Timer started successfully
        schema:
          type: object
          properties:
            status:
              type: string
            session_id:
              type: integer
            started_at:
              type: string
              format: date-time
      400:
        description: Invalid request
        schema:
          type: object
          properties:
            error:
              type: string
    """
