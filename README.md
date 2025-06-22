# Nutrition Tracker

A comprehensive nutrition and fitness tracking application with AI-powered features.

## Features

- **Nutrition Tracking**: Track meals, calories, and macronutrients
- **Recipe Management**: Create and manage recipes with AI assistance
- **Gym Tracking**: Log workouts with intelligent progression suggestions
- **Analytics**: Comprehensive dashboard with insights and trends
- **AI Assistant**: Get personalized nutrition and fitness recommendations

## Quick Start

1. Install dependencies: `pip install -r requirements.txt`
2. Set up environment variables (see `env.example`)
3. Run the application: `python app.py`

## Documentation

See the `docs/` folder for detailed documentation:
- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md)
- [Brand Guidelines](docs/BRAND_BOOK_MVP.md)
- [Database Guide](docs/DATABASE_PERSISTENCE_GUIDE.md)
- [Recipe Features](docs/RECIPE_FEATURES_GUIDE.md)
- [Voice Input](docs/VOICE_INPUT_GUIDE.md)

## Technology Stack

- **Backend**: Flask, MySQL
- **Frontend**: HTML, CSS, JavaScript, Bootstrap
- **AI**: OpenAI GPT integration
- **Database**: MySQL (production), SQLite (development fallback)

## Project Structure

```
nutrition_tracker/
├── app.py              # Main application
├── config/             # Configuration files
├── models/             # Data models and services
├── templates/          # HTML templates
├── static/             # CSS, JS, images
├── docs/               # Documentation
└── tests/              # Test files
```
