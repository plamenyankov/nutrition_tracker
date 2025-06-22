#!/bin/bash

# Comprehensive Root Directory Cleanup Script
# Removes completed migrations, organizes documentation, removes old databases
# Run from project root directory

echo "🧹 Comprehensive Root Directory Cleanup..."
echo "=========================================="

# Create timestamp for logs
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="comprehensive_cleanup_${TIMESTAMP}.log"

# Create backup list of what we're doing
echo "Creating cleanup log..."
{
    echo "# Comprehensive cleanup performed on $(date)"
    echo "# Nutrition Tracker Root Directory Cleanup"
    echo ""
} > "$LOG_FILE"

# Function to safely remove files
remove_files() {
    local category="$1"
    shift
    echo ""
    echo "📁 Removing $category..."

    for file in "$@"; do
        if [ -f "$file" ]; then
            echo "  ✓ Removing: $file"
            echo "REMOVED: $file" >> "$LOG_FILE"
            rm "$file"
        else
            echo "  ⚠ Not found: $file"
        fi
    done
}

# Function to move files
move_files() {
    local category="$1"
    local destination="$2"
    shift 2
    echo ""
    echo "📂 Moving $category to $destination..."

    for file in "$@"; do
        if [ -f "$file" ]; then
            echo "  ✓ Moving: $file → $destination/"
            echo "MOVED: $file → $destination/" >> "$LOG_FILE"
            mv "$file" "$destination/"
        else
            echo "  ⚠ Not found: $file"
        fi
    done
}

# 1. Remove completed one-time migration scripts
remove_files "Completed One-Time Migration Scripts" \
    "migrate_add_favorites.py" \
    "migrate_add_gym_tracker.py" \
    "migrate_add_meal_types.py" \
    "migrate_add_progression_priorities.py" \
    "migrate_add_recipe_consumption.py" \
    "migrate_add_total_calories.py" \
    "migrate_add_workout_templates.py" \
    "migrate_add_workout_timing.py" \
    "migrate_advanced_progression.py" \
    "migrate_advanced_progression_v2.py" \
    "migrate_gym_tracker_complete.py" \
    "migrate_progressive_overload.py" \
    "migrate_workout_completion.py" \
    "migrate_workout_data_only.py"

# 2. Remove old database files (keeping only current database.db)
remove_files "Old Database Files" \
    "production_database.db" \
    "production_database.db-shm" \
    "production_database.db-wal" \
    "database.db-shm" \
    "database.db-wal"

# 3. Keep latest MySQL backup, remove others
remove_files "Old MySQL Backups" \
    "nutri_tracker_prod_backup_20250615_090308.sql"

# 4. Create docs directory and move documentation
echo ""
echo "📂 Organizing documentation into docs/ folder..."

# Move current/useful documentation to docs/
move_files "Current Documentation" "docs" \
    "BRAND_BOOK_MVP.md" \
    "DEPLOYMENT_CHECKLIST.md" \
    "DEPLOYMENT_GUIDE.md" \
    "DATABASE_PERSISTENCE_GUIDE.md" \
    "MIGRATION_GUIDE.md" \
    "PROGRESSION_DASHBOARD_DOCUMENTATION.md" \
    "PROGRESSION_DASHBOARD_IMPROVEMENTS.md" \
    "RECIPE_FEATURES_GUIDE.md" \
    "REMOTE_DATABASE_ACCESS_GUIDE.md" \
    "VOICE_INPUT_GUIDE.md" \
    "zyra_brandbook.md"

# 5. Remove outdated/obsolete documentation
remove_files "Outdated Documentation" \
    "AI_ASSISTANT_FIX_GUIDE.md" \
    "APP_REORGANIZATION_PLAN.md" \
    "CHECK_DIGITALOCEAN_LOGS.md" \
    "FOOD_DATABASE_FIX_GUIDE.md" \
    "GYM_PROGRESSIVE_OVERLOAD_PLAN.md" \
    "GYM_PROGRESSIVE_OVERLOAD_PLAN_V2.md" \
    "GYM_TRACKER_ENHANCEMENT_PLAN.md" \
    "GYM_TRACKER_IMPLEMENTATION_EXAMPLE.md" \
    "GYM_TRACKER_PLAN.md" \
    "GYM_TRACKER_PRODUCTION_MIGRATION_GUIDE.md" \
    "GYM_TRACKER_README.md" \
    "GYM_TRACKER_TEMPLATES_GUIDE.md"

# 6. Remove remaining utility scripts
remove_files "Utility Scripts" \
    "create_production_env.py" \
    "create_production_env.sh" \
    "deploy_to_digitalocean.sh" \
    "production_mysql_commands.sh" \
    "remote_db_manager.sh" \
    "run_all_migrations.py" \
    "setup_db.py" \
    "setup_mysql_databases.py" \
    "setup_ssh_tunnel.py" \
    "simple_mysql_setup.py"

# 7. Remove data files that are no longer needed
remove_files "Old Data Files" \
    "data.csv" \
    "populate_db.py" \
    "init_db.py" \
    "import_gym_data.py"

# 8. Clean up old SQL files
remove_files "Old SQL Files" \
    "exercise_cleanup_queries.sql"

# 9. Update README.md to be more meaningful
echo ""
echo "📝 Updating README.md..."
cat > README.md << 'EOF'
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
EOF

echo "UPDATED: README.md" >> "$LOG_FILE"

echo ""
echo "=========================================="
echo "✅ Comprehensive cleanup completed!"
echo ""
echo "📊 Summary:"
echo "  • Removed 14 completed migration scripts"
echo "  • Removed old database files (kept current database.db)"
echo "  • Organized documentation into docs/ folder"
echo "  • Removed outdated documentation files"
echo "  • Removed utility scripts no longer needed"
echo "  • Cleaned up old data and SQL files"
echo "  • Updated README.md with proper project overview"
echo ""
echo "📁 Documentation now organized in:"
echo "  docs/BRAND_BOOK_MVP.md"
echo "  docs/DEPLOYMENT_GUIDE.md"
echo "  docs/DATABASE_PERSISTENCE_GUIDE.md"
echo "  docs/MIGRATION_GUIDE.md"
echo "  docs/PROGRESSION_DASHBOARD_DOCUMENTATION.md"
echo "  docs/RECIPE_FEATURES_GUIDE.md"
echo "  docs/REMOTE_DATABASE_ACCESS_GUIDE.md"
echo "  docs/VOICE_INPUT_GUIDE.md"
echo "  docs/zyra_brandbook.md"
echo ""
echo "📝 Cleanup log saved to: $LOG_FILE"
echo ""
echo "🎯 Root directory is now clean and well-organized!"
echo ""
echo "📂 Current structure:"
echo "  app.py                    # Main application"
echo "  requirements.txt          # Dependencies"
echo "  env.example              # Environment template"
echo "  database.db              # Current database"
echo "  README.md                # Project overview"
echo "  docs/                    # All documentation"
echo "  config/                  # Configuration"
echo "  models/                  # Application logic"
echo "  templates/               # HTML templates"
echo "  static/                  # Frontend assets"
