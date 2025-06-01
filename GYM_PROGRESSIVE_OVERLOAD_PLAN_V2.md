# Progressive Overload Implementation Plan V2
## Advanced Set-Specific Progression System

### Key Concepts

#### 1. Pyramid Training Recognition
Most lifters use pyramid schemes:
- **Ascending Pyramid**: Weight increases each set (40kg→50kg→60kg)
- **Descending Pyramid**: Weight decreases each set (60kg→50kg→40kg)
- **Double Pyramid**: Up then down (40kg→50kg→60kg→50kg)

#### 2. Set-Specific Progression
Each set can progress independently:
```
Week 1: Set 1: 40kg × 12 reps
        Set 2: 50kg × 10 reps
        Set 3: 60kg × 8 reps

Week 2: Set 1: 42.5kg × 12 reps (progressed!)
        Set 2: 50kg × 11 reps (getting there)
        Set 3: 60kg × 8 reps (maintaining)
```

#### 3. Progression Priority Hierarchy
1. **Reps** - Increase reps while maintaining weight
2. **Weight** - Increase weight when rep target is achieved
3. **Volume** - Total weight × reps across all sets
4. **Sets** - Add more sets to the exercise
5. **Exercises** - Add additional exercises for the muscle group

### Set Progression as Progressive Overload

Adding sets is a powerful progression method that allows for volume increase without compromising form:

#### Example Set Progression Timeline:
```
Month 1: Bench Press - 3 sets
  Week 1-2: 40kg×12, 50kg×10, 60kg×8
  Week 3-4: 40kg×15, 50kg×13, 60kg×10 (reps increased)

Month 2: Add 4th set
  Week 5-6: 42.5kg×12, 52.5kg×11, 60kg×10, 65kg×6 (new set!)
  Week 7-8: 42.5kg×14, 52.5kg×12, 60kg×11, 65kg×8

Month 3: Consolidate or add 5th set
  Week 9-10: Increase weights on all sets
  Week 11-12: Consider 5th set if recovery allows
```

#### Set Addition Criteria:
- Consistently hitting rep targets on all current sets
- Good form maintained throughout
- Recovery between workouts is adequate
- No joint pain or excessive fatigue
- Volume increase aligns with training phase

#### Smart Set Progression Rules:
1. **New Set Weight**: Start 5-10% lighter than previous set
2. **New Set Reps**: Aim for 6-8 reps initially
3. **Progression Order**: Master current sets before adding new ones
4. **Volume Cap**: Max 5-6 working sets per exercise (diminishing returns)
5. **Deload**: Every 4-6 weeks, reduce to baseline sets

### Database Schema Updates

```sql
-- Update workout_sets to track progression readiness
ALTER TABLE workout_sets ADD COLUMN target_reps INTEGER;
ALTER TABLE workout_sets ADD COLUMN progression_ready BOOLEAN DEFAULT 0;
ALTER TABLE workout_sets ADD COLUMN last_progression_date DATE;

-- Set-specific progression tracking
CREATE TABLE set_progression_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    exercise_id INTEGER NOT NULL,
    set_number INTEGER NOT NULL,
    progression_date DATE NOT NULL,
    old_weight REAL,
    new_weight REAL,
    old_reps INTEGER,
    new_reps INTEGER,
    progression_type TEXT, -- 'weight', 'reps', 'added_set'
    notes TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (exercise_id) REFERENCES exercises(id)
);

-- Exercise-specific progression patterns
CREATE TABLE exercise_progression_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    exercise_id INTEGER NOT NULL,
    pattern_type TEXT, -- 'ascending', 'descending', 'straight', 'double_pyramid'
    typical_sets INTEGER DEFAULT 3, -- Current typical number, can grow
    detected_pattern TEXT,
    confidence_score REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (exercise_id) REFERENCES exercises(id),
    UNIQUE(user_id, exercise_id)
);

-- Set-specific pattern ratios (flexible for any number of sets)
CREATE TABLE set_pattern_ratios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_id INTEGER NOT NULL,
    set_number INTEGER NOT NULL,
    weight_ratio REAL DEFAULT 1.0, -- Relative to user's working weight
    typical_reps INTEGER,
    notes TEXT,
    FOREIGN KEY (pattern_id) REFERENCES exercise_progression_patterns(id) ON DELETE CASCADE,
    UNIQUE(pattern_id, set_number)
);

-- Volume tracking for progression analysis
CREATE TABLE workout_volume_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_id INTEGER NOT NULL,
    exercise_id INTEGER NOT NULL,
    total_volume REAL, -- sum of weight × reps
    total_reps INTEGER,
    total_sets INTEGER,
    avg_intensity REAL, -- average weight used
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workout_id) REFERENCES workout_sessions(id),
    FOREIGN KEY (exercise_id) REFERENCES exercises(id)
);
```

### Advanced Progression Algorithm

```python
class AdvancedProgressionService:
    def analyze_set_progression(self, user_id, exercise_id, set_number):
        """Analyze progression readiness for a specific set"""
        # Get last 3 performances for this specific set
        history = self.get_set_history(user_id, exercise_id, set_number, limit=3)

        # Check if ready for progression based on:
        # 1. Consistently hitting target reps
        # 2. Form quality is good (if tracked)
        # 3. Recovery is adequate (days between workouts)

        return {
            'ready': ready_status,
            'suggestion': suggestion_type,
            'confidence': confidence_score
        }

    def get_pyramid_pattern(self, user_id, exercise_id):
        """Detect the user's typical pyramid pattern"""
        recent_workouts = self.get_recent_workouts(user_id, exercise_id, limit=5)

        # Analyze weight progression across sets
        patterns = []
        for workout in recent_workouts:
            if len(workout.sets) >= 2:
                weight_diffs = [workout.sets[i+1].weight - workout.sets[i].weight
                               for i in range(len(workout.sets)-1)]

                if all(diff > 0 for diff in weight_diffs):
                    patterns.append('ascending')
                elif all(diff < 0 for diff in weight_diffs):
                    patterns.append('descending')
                elif all(abs(diff) < 2.5 for diff in weight_diffs):
                    patterns.append('straight')
                else:
                    patterns.append('mixed')

        # Return most common pattern
        return max(set(patterns), key=patterns.count)

    def calculate_volume_progression(self, user_id, exercise_id):
        """Track volume progression over time"""
        volume_history = self.get_volume_history(user_id, exercise_id, days=30)

        # Calculate trends
        volume_trend = self.calculate_trend(volume_history)
        intensity_trend = self.calculate_intensity_trend(volume_history)

        return {
            'volume_increasing': volume_trend > 0,
            'intensity_increasing': intensity_trend > 0,
            'total_volume_change': f"{volume_trend:+.1f}%",
            'suggestion': self.get_volume_suggestion(volume_trend, intensity_trend)
        }
```

### UI Components

#### 1. Set-Specific Progression Indicators
```html
<!-- In workout edit template -->
<div class="set-row">
    <span class="set-number">Set 1</span>
    <input type="number" value="40" class="weight-input">
    <span class="progression-indicator">
        {% if set.ready_for_progression %}
            <i class="fas fa-arrow-up text-success"></i>
            Ready: Try 42.5kg
        {% elif set.close_to_progression %}
            <i class="fas fa-chart-line text-warning"></i>
            1-2 more workouts
        {% endif %}
    </span>
</div>
```

#### 2. Progression Dashboard
```
┌─────────────────────────────────────┐
│ Bench Press Progression Analysis    │
├─────────────────────────────────────┤
│ Pattern: Ascending Pyramid          │
│ Current: 3 sets (40→50→60kg)       │
│                                     │
│ Set 1: 40kg × 15 ✅ Ready          │
│        → Suggest: 42.5kg × 12      │
│                                     │
│ Set 2: 50kg × 12 📈 Almost there   │
│        → Target: 50kg × 13-15      │
│                                     │
│ Set 3: 60kg × 8 🔄 Maintaining     │
│        → Focus: Form & consistency │
│                                     │
│ Volume Trend: +12% this month 📊    │
│ Next Goal: Add 4th set at 65kg?    │
└─────────────────────────────────────┘
```

#### 3. Progression Priority Settings
```
Progression Priorities (drag to reorder):
1. ⬆️ Increase Reps (default)
2. 💪 Increase Weight
3. 📊 Increase Total Volume
4. ➕ Add More Sets
5. 🎯 Add New Exercises

Pyramid Preference:
○ Ascending (light → heavy)
● Straight Sets (same weight)
○ Descending (heavy → light)
○ Let AI detect my pattern
```

### Implementation Phases

#### Phase 1: Enhanced Data Model (Week 1)
- [ ] Create new database tables
- [ ] Update workout_sets schema
- [ ] Create migration scripts
- [ ] Update models with set-specific tracking

#### Phase 2: Set-Specific Tracking (Week 2)
- [ ] Modify workout logging to track set-specific targets
- [ ] Update GymService with set-specific methods
- [ ] Create SetProgressionService class
- [ ] Add pyramid pattern detection

#### Phase 3: Advanced Algorithm (Week 3)
- [ ] Implement multi-factor progression analysis
- [ ] Create volume tracking system
- [ ] Build confidence scoring for suggestions
- [ ] Add recovery time considerations

#### Phase 4: UI Enhancements (Week 4)
- [ ] Add set-specific progression indicators
- [ ] Create progression dashboard
- [ ] Implement drag-and-drop priority settings
- [ ] Add volume/intensity charts

#### Phase 5: Testing & Refinement (Week 5)
- [ ] Test with various pyramid patterns
- [ ] Validate progression suggestions
- [ ] Fine-tune confidence algorithms
- [ ] Add user feedback collection

### Success Metrics
- Set-specific progression tracking adoption: >90%
- Progression suggestion accuracy: >80%
- User progression success rate: +25%
- Volume increases over 3 months: +15-20%

### Example Use Cases

#### Case 1: Bench Press Pyramid Progression
```
Week 1: 40kg×12, 50kg×10, 60kg×8
Week 2: 40kg×14, 50kg×10, 60kg×8
Week 3: 40kg×15, 50kg×11, 60kg×8
Week 4: 42.5kg×12, 50kg×12, 60kg×9 ← Progressed set 1!
```

#### Case 2: Volume-Based Progression
```
Week 1: Total Volume = 1,640kg (3 sets)
Week 2: Total Volume = 1,720kg (3 sets, more reps)
Week 3: Total Volume = 1,880kg (added 4th set)
Week 4: Total Volume = 1,950kg (increased weights)
```

#### Case 3: Straight Sets to Pyramid Transition
```
Beginner: 3×10 @ 40kg (straight sets)
Intermediate: 40kg×12, 45kg×10, 50kg×8
Advanced: 40kg×15, 50kg×12, 60kg×10, 65kg×8
```
