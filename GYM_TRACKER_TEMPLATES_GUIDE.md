# Workout Templates Feature Guide

## Overview
The Gym Tracker now supports **Workout Templates** - pre-configured workout plans that you can reuse. This feature allows you to:
- Create workout templates with preset exercises, sets, reps, and weights
- Start workouts from templates or create custom workouts
- Share templates publicly for others to use
- Save time by not having to recreate common workouts

## Features Added

### 1. Template Management
- **Create Templates**: Design reusable workout plans
- **Edit Templates**: Modify exercises, sets, reps, weights, and rest times
- **Delete Templates**: Remove templates you no longer need
- **Public/Private**: Choose whether to share templates with other users

### 2. Template Components
Each template includes:
- **Name & Description**: Identify and describe your workout
- **Exercises**: Ordered list of exercises
- **Sets**: Number of sets per exercise
- **Target Reps**: Suggested repetitions
- **Target Weight**: Recommended weight (optional)
- **Rest Time**: Rest duration between sets
- **Notes**: Special instructions per exercise

### 3. Starting Workouts
Two ways to start a workout:
- **From Template**: Pre-populated with all exercises and target values
- **Custom Workout**: Build as you go (original functionality)

## Database Schema

### New Tables Created

#### `workout_templates`
```sql
CREATE TABLE workout_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    user_id INTEGER,
    is_public BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `workout_template_exercises`
```sql
CREATE TABLE workout_template_exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id INTEGER NOT NULL,
    exercise_id INTEGER NOT NULL,
    order_index INTEGER NOT NULL,
    sets INTEGER DEFAULT 3,
    target_reps INTEGER,
    target_weight REAL,
    rest_seconds INTEGER DEFAULT 90,
    notes TEXT
);
```

### Modified Tables
- `workout_sessions`: Added `template_id` column to track which template was used

## How to Use

### Creating a Template
1. Go to **Gym Tracker** → **Templates**
2. Click **Create Template**
3. Enter name and description
4. Save and then add exercises
5. Configure sets, reps, weights for each exercise

### Using a Template
1. Click **Start Workout** from dashboard
2. Choose **Use Template**
3. Select a template (yours or public)
4. Workout will be pre-populated with all exercises
5. Adjust weights/reps as needed during workout

### Managing Templates
- **View**: See all template details
- **Edit**: Modify exercises and settings
- **Preview**: Check template before using
- **Delete**: Remove unwanted templates

## Routes Added

### Template Management
- `GET /gym/templates` - List all templates
- `GET/POST /gym/templates/create` - Create new template
- `GET /gym/templates/<id>` - View template details
- `GET /gym/templates/<id>/edit` - Edit template
- `POST /gym/templates/<id>/update` - Update template info
- `POST /gym/templates/<id>/delete` - Delete template

### Template Exercises
- `POST /gym/templates/<id>/add-exercise` - Add exercise to template
- `POST /gym/templates/exercise/<id>/update` - Update exercise in template
- `POST /gym/templates/exercise/<id>/remove` - Remove exercise from template

### Workout Flow
- `GET /gym/workout/choose` - Choose between template or custom
- `GET /gym/workout/start/<template_id>` - Start workout from template

## Example Templates

### Push Day Template (Public)
- Bench Press: 4 sets × 10 reps @ 60kg
- Incline Bench Press: 3 sets × 12 reps @ 50kg
- Overhead Press: 4 sets × 8 reps @ 40kg
- Rope Pushdown: 3 sets × 15 reps @ 20kg

### Custom Templates You Can Create
- **Full Body Beginner**: Basic compound movements
- **Upper/Lower Split**: Separate upper and lower body days
- **PPL (Push/Pull/Legs)**: Popular bodybuilding split
- **5x5 Strength**: Focus on heavy compound lifts
- **HIIT Circuit**: High-intensity interval training

## Benefits

1. **Time Saving**: No need to remember or recreate workouts
2. **Consistency**: Follow the same plan each time
3. **Progress Tracking**: See how weights increase over time
4. **Sharing**: Learn from public templates
5. **Flexibility**: Modify on the fly during workouts

## Tips

- Start with 2-3 basic templates
- Update target weights as you get stronger
- Use notes for form reminders
- Try public templates for inspiration
- Adjust rest times based on your fitness level

## Future Enhancements

Potential improvements:
- Template categories/tags
- Copy templates from other users
- Template scheduling/programs
- Progress tracking per template
- Export/import templates
