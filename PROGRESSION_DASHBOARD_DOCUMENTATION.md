# Progression Dashboard Documentation

## Overview
The Progression Dashboard (`/gym/progression/dashboard`) is the central analytics hub for tracking workout progression, training patterns, and performance trends. It provides a comprehensive view of your fitness journey through multiple data visualizations and metrics.

## Page Structure & Sections

### 1. Summary Metrics (Top Row)
**Location**: Four metric cards at the top of the page
**Purpose**: Quick overview of progression statistics

#### Data Sources & Logic:
- **Total Progressions**:
  - **Query**: `SELECT COUNT(*) FROM progression_history WHERE user_id = ?`
  - **Logic**: Counts all recorded progression events (weight increases, rep increases, set additions)
  - **Display**: Raw count number

- **This Month**:
  - **Query**: `SELECT COUNT(*) FROM progression_history WHERE user_id = ? AND progression_date >= ?`
  - **Logic**: Filters progressions to current month only (from 1st of current month)
  - **Display**: Count of progressions this month

- **Volume Increase**:
  - **Data Source**: `workout_volume_tracking` table
  - **Logic**: Compares first and last volume entries from past 30 days
  - **Calculation**: `((last_volume - first_volume) / first_volume) * 100`
  - **Display**: Percentage change with + prefix for increases

- **Exercises Progressed**:
  - **Logic**: Counts exercises where `progression_service.check_progression_readiness()` returns `ready: true`
  - **Display**: "X/Y" format (progressed/total exercises)

### 2. Training Patterns Section
**Location**: Grid of pattern cards below metrics
**Purpose**: Visual representation of user's training patterns per exercise

#### Data Sources & Logic:
- **Primary Query**:
  ```sql
  SELECT e.id, e.name, e.muscle_group, epp.pattern_type,
         epp.typical_sets, epp.confidence_score
  FROM exercises e
  LEFT JOIN exercise_progression_patterns epp
      ON e.id = epp.exercise_id AND epp.user_id = ?
  WHERE e.id IN (SELECT DISTINCT exercise_id FROM workout_sets...)
  ```

- **Pattern Detection**:
  - If no stored pattern exists, calls `AdvancedProgressionService.detect_pyramid_pattern()`
  - Analyzes last 5 workouts to determine weight progression across sets
  - **Ascending**: Weight increases each set (40kg→50kg→60kg)
  - **Descending**: Weight decreases each set (60kg→50kg→40kg)
  - **Straight**: Same weight all sets (50kg×3 sets)
  - **Mixed**: Variable/inconsistent pattern

- **Confidence Score**:
  - Calculated as: `pattern_occurrences / total_workouts_analyzed`
  - Range: 0.0 to 1.0 (displayed as percentage)

- **Visual Indicators**:
  - **Green border**: Ascending pattern
  - **Red border**: Descending pattern
  - **Blue border**: Straight sets
  - **Yellow border**: Mixed/Pyramid pattern

### 3. Volume Trends Chart
**Location**: Large chart on left side of lower section
**Purpose**: Time-series visualization of training volume and intensity

#### Data Sources & Logic:
- **Query**:
  ```sql
  SELECT ws.date, SUM(vt.total_volume), AVG(vt.avg_intensity)
  FROM workout_sessions ws
  JOIN workout_volume_tracking vt ON ws.id = vt.workout_id
  WHERE ws.user_id = ? AND ws.date >= ?
  GROUP BY ws.date
  ORDER BY ws.date
  ```

- **Chart Configuration**:
  - **Type**: Line chart with dual Y-axes
  - **Left Y-axis**: Total Volume (kg) - sum of weight × reps for all exercises
  - **Right Y-axis**: Average Intensity (kg) - average weight used across exercises
  - **Time Range**: Last 30 days
  - **Data Points**: One per workout day

- **Volume Calculation**:
  - Per exercise: `SUM(weight × reps)` for all sets
  - Per workout: Sum of all exercise volumes
  - Stored in `workout_volume_tracking.total_volume`

- **Intensity Calculation**:
  - Per exercise: `AVG(weight)` across all sets
  - Per workout: Average of all exercise intensities
  - Stored in `workout_volume_tracking.avg_intensity`

### 4. Recent Progressions Timeline
**Location**: Right sidebar of lower section
**Purpose**: Chronological list of recent progression events

#### Data Sources & Logic:
- **Query**:
  ```sql
  SELECT ph.progression_date, e.name, ph.progression_type,
         ph.old_weight, ph.new_weight
  FROM progression_history ph
  JOIN exercises e ON ph.exercise_id = e.id
  WHERE ph.user_id = ?
  ORDER BY ph.progression_date DESC
  LIMIT 10
  ```

- **Event Types**:
  - **Weight Progression**: Shows "40kg → 42.5kg"
  - **Rep Progression**: Shows "10 → 12 reps"
  - **Set Addition**: Shows "Added set 4"

- **Visual Elements**:
  - **Timeline dots**: Green for weight increases, blue for others
  - **Date stamps**: Formatted workout dates
  - **Exercise names**: Linked to detailed progression view

### 5. Exercise Progress Cards
**Location**: Bottom grid section
**Purpose**: Individual exercise progression status and metrics

#### Data Sources & Logic:
- **Base Query**: Gets all exercises user has performed
- **For each exercise**:
  - **Progression Readiness**: `ProgressionService.check_progression_readiness()`
  - **Current Performance**: `GymService.get_last_exercise_performance()`
  - **Volume Trend**: `AdvancedProgressionService.get_volume_trend()`

- **Status Badges**:
  - **Ready (Green)**: `readiness.ready == True`
  - **Close (Yellow)**: `readiness.suggestion == 'increase_reps'`
  - **Building (Gray)**: Default state, still building strength

- **Progress Bar**:
  - **Calculation**: `(current_avg_reps / target_reps) * 100`
  - **Colors**: Green (≥80%), Yellow (≥50%), Gray (<50%)

- **Volume Trend**:
  - **Calculation**: 30-day volume change percentage
  - **Colors**: Green (positive), Red (negative), Gray (neutral)

## Backend Services Integration

### AdvancedProgressionService
- **Pattern Detection**: Analyzes workout history to identify training patterns
- **Volume Tracking**: Calculates and stores volume metrics per workout
- **Set Analysis**: Provides set-specific progression recommendations

### ProgressionService
- **Readiness Assessment**: Determines if exercises are ready for progression
- **User Preferences**: Manages progression strategy and rep targets
- **History Tracking**: Records and retrieves progression events

### GymService
- **Performance Data**: Provides last performance metrics per exercise
- **Workout Data**: Manages workout sessions and exercise data

## Database Tables Used

### Core Tables:
- `progression_history`: Stores all progression events
- `exercise_progression_patterns`: Cached pattern analysis results
- `workout_volume_tracking`: Pre-calculated volume metrics
- `workout_sessions`: Workout metadata and dates
- `workout_sets`: Individual set data (weight, reps)
- `exercises`: Exercise definitions and muscle groups

### Key Relationships:
```
workout_sessions (1) → (many) workout_sets
workout_sessions (1) → (many) workout_volume_tracking
exercises (1) → (many) workout_sets
exercises (1) → (many) progression_history
users (1) → (many) progression_history
```

## Performance Optimizations

### Data Caching:
- Pattern analysis results stored in `exercise_progression_patterns`
- Volume metrics pre-calculated in `workout_volume_tracking`
- Confidence scores cached to avoid repeated calculations

### Query Efficiency:
- Uses JOINs to minimize database round trips
- Limits result sets (e.g., last 10 progressions, 30 days of data)
- Indexes on user_id, exercise_id, and date columns

### Frontend Optimization:
- Chart.js for efficient data visualization
- Responsive design with mobile-optimized layouts
- Progressive loading of chart data

## User Experience Features

### Interactive Elements:
- **Clickable exercise cards**: Navigate to detailed progression view
- **Hover effects**: Visual feedback on pattern cards
- **Responsive charts**: Zoom and pan capabilities
- **Real-time updates**: Data refreshes on page reload

### Visual Hierarchy:
- **Color coding**: Consistent across all progression states
- **Typography**: Clear metric values with descriptive labels
- **Spacing**: Logical grouping of related information
- **Icons**: Intuitive symbols for different progression types

## Future Enhancement Opportunities

### Potential Additions:
1. **Real-time updates**: WebSocket integration for live data
2. **Goal tracking**: Progress toward specific strength targets
3. **Comparison views**: Month-over-month progression analysis
4. **Export functionality**: PDF reports and data export
5. **Social features**: Progress sharing and comparisons
6. **Predictive analytics**: ML-based progression forecasting

### Technical Improvements:
1. **Caching layer**: Redis for frequently accessed data
2. **Background processing**: Async volume calculations
3. **API endpoints**: RESTful API for mobile app integration
4. **Data aggregation**: Pre-computed weekly/monthly summaries
