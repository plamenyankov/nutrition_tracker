# Gym Tracker Implementation Plan

## Overview
Add a simple gym workout tracking module to the existing nutrition tracker app that allows users to:
- Manage exercises
- Create workout templates
- Log workout sessions with sets, reps, and weights

## Database Schema

### 1. Create New Tables

#### exercises
```sql
CREATE TABLE exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    muscle_group TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### workout_templates
```sql
CREATE TABLE workout_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    user_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

#### workout_template_exercises
```sql
CREATE TABLE workout_template_exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id INTEGER,
    exercise_id INTEGER,
    order_index INTEGER,
    FOREIGN KEY (template_id) REFERENCES workout_templates(id),
    FOREIGN KEY (exercise_id) REFERENCES exercises(id)
);
```

#### workout_sessions
```sql
CREATE TABLE workout_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    template_id INTEGER,
    date DATE NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (template_id) REFERENCES workout_templates(id)
);
```

#### workout_sets
```sql
CREATE TABLE workout_sets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    exercise_id INTEGER,
    set_number INTEGER,
    weight REAL,
    reps INTEGER,
    FOREIGN KEY (session_id) REFERENCES workout_sessions(id),
    FOREIGN KEY (exercise_id) REFERENCES exercises(id)
);
```

## Implementation Tasks

### Phase 1: Database Setup
- [ ] Create migration script for new tables
- [ ] Populate exercises table with common exercises from CSV data
- [ ] Update database initialization script

### Phase 2: Models
- [ ] Create Exercise model
- [ ] Create WorkoutTemplate model
- [ ] Create WorkoutSession model
- [ ] Create WorkoutSet model

### Phase 3: Core Features

#### 3.1 Exercise Management
- [ ] Create route to add new exercise
- [ ] Create route to list all exercises
- [ ] Create simple form for adding exercises
- [ ] Create exercise list view

#### 3.2 Workout Templates
- [ ] Create route to create workout template
- [ ] Create route to list user's workout templates
- [ ] Create form to build workout (select exercises)
- [ ] Create template list view

#### 3.3 Workout Logging
- [ ] Create route to start new workout session
- [ ] Create route to log sets (weight & reps)
- [ ] Create workout logging interface
- [ ] Create route to save completed workout

#### 3.4 Workout History
- [ ] Create route to view workout history
- [ ] Create calendar/list view of past workouts
- [ ] Create detailed workout view

### Phase 4: Basic UI Components

#### Templates Structure
```
templates/
└── gym/
    ├── exercises/
    │   ├── list.html
    │   └── add.html
    ├── workouts/
    │   ├── create.html
    │   ├── list.html
    │   └── log.html
    └── history/
        ├── list.html
        └── detail.html
```

### Phase 5: Integration
- [ ] Add "Gym Tracker" to main navigation
- [ ] Create gym dashboard page
- [ ] Link gym tracker to user authentication
- [ ] Add basic statistics (total workouts, favorite exercises)

## MVP Routes

### Exercise Routes
- `GET /gym/exercises` - List all exercises
- `POST /gym/exercises` - Add new exercise
- `GET /gym/exercises/add` - Show add exercise form

### Workout Routes
- `GET /gym/workouts` - List user's workout templates
- `GET /gym/workouts/create` - Show create workout form
- `POST /gym/workouts` - Save new workout template
- `GET /gym/workouts/<id>/start` - Start workout session
- `POST /gym/workouts/<id>/log` - Log sets for workout

### History Routes
- `GET /gym/history` - Show workout history
- `GET /gym/history/<id>` - Show specific workout details

## Sample Code Structure

### models/gym.py
```python
# Exercise model
# WorkoutTemplate model
# WorkoutSession model
# WorkoutSet model
```

### blueprints/gym.py
```python
# Routes for gym tracker
# Exercise management
# Workout creation and logging
# History viewing
```

## Data Import Task (Optional)
- [ ] Create CSV parser for existing workout data
- [ ] Import historical workout data
- [ ] Map exercise names from CSV to exercise table

## Future Enhancements (Post-MVP)
- Progress charts and analytics
- Exercise instruction/notes
- Rest timer between sets
- Personal records tracking
- Workout plan scheduling
- Export workout data

## Success Criteria
1. Users can add and view exercises
2. Users can create workout templates with multiple exercises
3. Users can log workouts with sets, reps, and weights
4. Users can view their workout history
5. All gym data is linked to authenticated users
