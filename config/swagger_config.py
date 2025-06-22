"""
Swagger configuration for Nutrition Tracker API
"""

swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec',
            "route": '/apispec.json',
            "rule_filter": lambda rule: True,  # all in
            "model_filter": lambda tag: True,  # all in
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs"
}

swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "Nutrition Tracker API",
        "description": "Comprehensive nutrition and fitness tracking application with AI-powered features",
        "version": "1.0.0",
        "contact": {
            "name": "Nutrition Tracker",
            "url": "https://github.com/yourusername/nutrition_tracker"
        }
    },
    "host": "localhost:5000",
    "basePath": "/",
    "schemes": ["http", "https"],
    "securityDefinitions": {
        "LoginRequired": {
            "type": "apiKey",
            "name": "session",
            "in": "cookie",
            "description": "Flask-Login session authentication"
        }
    },
    "security": [
        {"LoginRequired": []}
    ],
    "tags": [
        {
            "name": "Authentication",
            "description": "User authentication endpoints"
        },
        {
            "name": "Food Database",
            "description": "Food and ingredient management"
        },
        {
            "name": "Meal Tracking",
            "description": "Daily meal and consumption tracking"
        },
        {
            "name": "Recipes",
            "description": "Recipe creation and management"
        },
        {
            "name": "Gym Tracking",
            "description": "Workout and exercise tracking"
        },
        {
            "name": "Progression",
            "description": "Workout progression analysis and suggestions"
        },
        {
            "name": "AI Assistant",
            "description": "AI-powered nutrition recommendations"
        },
        {
            "name": "Analytics",
            "description": "Data analytics and insights"
        },
        {
            "name": "Timer",
            "description": "Workout timing functionality"
        }
    ]
}
