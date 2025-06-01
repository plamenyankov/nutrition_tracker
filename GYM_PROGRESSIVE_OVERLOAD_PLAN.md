# Progressive Overload Implementation Plan

## Overview
Progressive overload is the gradual increase of stress placed on the body during exercise training. It's fundamental for continuous improvement in strength, muscle size, and endurance.

## Research Summary

### What is Progressive Overload?
- **Definition**: Gradually increasing workout intensity by manipulating variables like weight, reps, sets, or rest time
- **Purpose**: Forces the body to adapt, leading to strength and muscle gains
- **Key Principle**: "Doing slightly more than last time"

### Benefits
1. **Continuous strength gains** - Prevents plateaus
2. **Muscle hypertrophy** - Promotes muscle growth
3. **Improved neuromuscular adaptations** - Better muscle coordination
4. **Increased bone density** - Stronger skeletal system
5. **Enhanced motivation** - Clear progress tracking

### Progressive Overload Methods
1. **Increase weight** (most common)
2. **Increase reps** (your preferred method)
3. **Increase sets**
4. **Decrease rest time**
5. **Increase frequency**
6. **Improve form/range of motion**
7. **Slow down tempo**
8. **Use more difficult variations**

## Your Strategy Validation

Your approach of **10 → 15 reps → increase weight → back to 10 reps** is scientifically sound:

- ✅ **Research-backed**: Studies show rep progression is equally effective as weight progression
- ✅ **Safety-first**: Lower injury risk by mastering form before adding weight
- ✅ **Ideal for hypertrophy**: 10-15 rep range is optimal for muscle growth
- ✅ **Clear progression markers**: Easy to know when to advance (reaching 15 reps)
- ✅ **Sustainable**: Allows for continuous long-term progress

## Implementation Plan

### Phase 1: Gym Preferences Settings Page

#### 1.1 Create User Preferences Model
```python
class UserGymPreferences:
    - user_id (FK)
    - progression_strategy (enum: 'reps_first', 'weight_first', 'hybrid')
    - min_reps_target (default: 10)
    - max_reps_target (default: 15)
    - weight_increment_lower_body (default: 5kg)
    - weight_increment_upper_body (default: 2.5kg)
    - rest_timer_enabled (boolean)
    - progression_notification_enabled (boolean)
    - created_at
    - updated_at
```

#### 1.2 Progressive Overload Rules Model
```python
class ProgressionRules:
    - user_id (FK)
    - exercise_id (FK)
    - custom_min_reps (nullable)
    - custom_max_reps (nullable)
    - custom_weight_increment (nullable)
    - notes
```

### Phase 2: Exercise History & Analytics

#### 2.1 Exercise Performance View
```python
class ExercisePerformanceHistory:
    - get_last_n_performances(exercise_id, n=5)
    - calculate_average_performance(exercise_id, date_range)
    - detect_progression_readiness(exercise_id)
    - get_personal_records(exercise_id)
```

#### 2.2 Progression Detection Algorithm
```python
def check_progression_readiness(exercise_id, user_id):
    """
    Returns progression suggestion based on user's strategy
    """
    last_performances = get_last_3_workouts(exercise_id)
    user_prefs = get_user_preferences(user_id)

    if user_prefs.progression_strategy == 'reps_first':
        # Check if user hit max_reps for all sets in last 2 workouts
        if all_sets_hit_target_reps(last_performances, user_prefs.max_reps_target):
            return {
                'ready': True,
                'suggestion': 'increase_weight',
                'amount': get_weight_increment(exercise_id)
            }

    return calculate_next_targets()
```

### Phase 3: UI/UX Components

#### 3.1 Settings Page Layout
```
Gym Preferences
├── Progression Strategy
│   ├── [x] Reps First (10-15 method)
│   ├── [ ] Weight First
│   └── [ ] Custom
├── Rep Ranges
│   ├── Minimum Reps: [10] ▼
│   └── Maximum Reps: [15] ▼
├── Weight Increments
│   ├── Upper Body: [2.5] kg
│   └── Lower Body: [5.0] kg
└── Notifications
    └── [x] Suggest when ready to progress
```

#### 3.2 Workout Interface Enhancements
```
┌─────────────────────────────────┐
│ Bench Press                     │
│ Last: 60kg × 12,11,10          │
│ Best: 65kg × 8                 │
│ --------------------------------│
│ 📊 Progress: 12/15 reps avg    │
│ 💡 3 more workouts to progress │
│ 📈 Target: 60kg × 13-15 reps   │
└─────────────────────────────────┘
```

#### 3.3 Progression Celebration Modal
```
🎉 Progression Achieved!
You've consistently hit 15 reps on Bench Press

Ready to level up?
Current: 60kg × 15 reps
Suggested: 62.5kg × 10 reps

[Accept Progression] [Keep Current]
```

### Phase 4: Database Schema Updates

#### 4.1 New Tables
```sql
-- User gym preferences
CREATE TABLE user_gym_preferences (
    user_id INTEGER PRIMARY KEY,
    progression_strategy TEXT DEFAULT 'reps_first',
    min_reps_target INTEGER DEFAULT 10,
    max_reps_target INTEGER DEFAULT 15,
    weight_increment_upper REAL DEFAULT 2.5,
    weight_increment_lower REAL DEFAULT 5.0,
    rest_timer_enabled BOOLEAN DEFAULT 1,
    progression_notification_enabled BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Exercise-specific progression rules
CREATE TABLE exercise_progression_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    exercise_id INTEGER NOT NULL,
    custom_min_reps INTEGER,
    custom_max_reps INTEGER,
    custom_weight_increment REAL,
    notes TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (exercise_id) REFERENCES exercises(id),
    UNIQUE(user_id, exercise_id)
);

-- Progression history tracking
CREATE TABLE progression_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    exercise_id INTEGER NOT NULL,
    progression_date DATE NOT NULL,
    old_weight REAL,
    new_weight REAL,
    old_reps INTEGER,
    new_reps INTEGER,
    progression_type TEXT, -- 'weight_increase', 'reps_increase', etc.
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (exercise_id) REFERENCES exercises(id)
);
```

#### 4.2 Add to existing tables
```sql
-- Add to workout_sets
ALTER TABLE workout_sets ADD COLUMN rpe INTEGER; -- Rate of Perceived Exertion (1-10)
ALTER TABLE workout_sets ADD COLUMN form_quality INTEGER; -- 1-5 scale
```

### Phase 5: Backend Implementation

#### 5.1 New Service Methods
```python
class ProgressionService:
    def get_progression_suggestions(self, user_id, workout_id=None)
    def calculate_next_workout_targets(self, user_id, template_id)
    def record_progression(self, user_id, exercise_id, old_weight, new_weight)
    def get_exercise_trend(self, user_id, exercise_id, days=30)
    def predict_progression_date(self, user_id, exercise_id)
```

#### 5.2 API Endpoints
- `GET /gym/preferences` - Get user's gym preferences
- `POST /gym/preferences` - Update preferences
- `GET /gym/exercise/<id>/progression` - Get progression data
- `POST /gym/exercise/<id>/accept-progression` - Accept suggested progression
- `GET /gym/analytics/progression-summary` - Overall progression stats

### Phase 6: Features Implementation Tasks

#### Task 1: Create Preferences Infrastructure
- [ ] Create migration for new tables
- [ ] Build UserGymPreferences model
- [ ] Create ProgressionService class
- [ ] Add preference management routes

#### Task 2: Build Settings Page
- [ ] Create preferences template
- [ ] Add form validation
- [ ] Implement preference saving
- [ ] Add exercise-specific overrides

#### Task 3: Implement Progression Detection
- [ ] Build progression algorithm
- [ ] Create suggestion calculator
- [ ] Add notification system
- [ ] Test with various scenarios

#### Task 4: Enhance Workout UI
- [ ] Add progression indicators
- [ ] Show historical performance
- [ ] Display next targets
- [ ] Add quick progression buttons

#### Task 5: Create Analytics Dashboard
- [ ] Build progression timeline
- [ ] Show strength curves
- [ ] Display achievement badges
- [ ] Export progression data

#### Task 6: Mobile Optimization
- [ ] Responsive settings page
- [ ] Touch-friendly progression controls
- [ ] Swipe to see history
- [ ] Quick progression acceptance

## Success Metrics
- Users setting progression preferences: >80%
- Progression suggestions accepted: >70%
- Improved workout completion rate: +15%
- User retention increase: +20%

## Future Enhancements
1. **AI-powered suggestions** based on recovery and performance
2. **Deload week detection** when progress stalls
3. **Integration with wearables** for recovery metrics
4. **Social features** - share progression milestones
5. **Periodization planning** - long-term programming

## Timeline
- **Week 1-2**: Database schema and backend services
- **Week 3-4**: Settings page and preferences
- **Week 5-6**: Progression detection and UI enhancements
- **Week 7-8**: Testing, refinement, and deployment
