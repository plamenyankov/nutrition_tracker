# Gym Tracker Implementation Example

## Quick Start Implementation

### 1. Database Migration Script
Create `migrate_add_gym_tracker.py`:

```python
import sqlite3

def migrate():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Create exercises table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            muscle_group TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create workout_sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workout_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date DATE NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Create workout_sets table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workout_sets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            exercise_id INTEGER,
            set_number INTEGER,
            weight REAL,
            reps INTEGER,
            FOREIGN KEY (session_id) REFERENCES workout_sessions(id),
            FOREIGN KEY (exercise_id) REFERENCES exercises(id)
        )
    ''')

    # Populate initial exercises
    exercises = [
        ('Squat', 'Legs'),
        ('Bench Press', 'Chest'),
        ('Deadlift', 'Back'),
        ('Overhead Press', 'Shoulders'),
        ('Barbell Curls', 'Biceps'),
        ('Rope Pushdown', 'Triceps'),
        ('Leg Press', 'Legs'),
        ('Lat Pull Down', 'Back'),
        ('Dumbbell Press', 'Chest'),
        ('Leg Curls', 'Legs')
    ]

    cursor.executemany(
        'INSERT OR IGNORE INTO exercises (name, muscle_group) VALUES (?, ?)',
        exercises
    )

    conn.commit()
    conn.close()

if __name__ == '__main__':
    migrate()
    print("Gym tracker tables created successfully!")
```

### 2. Gym Service Model
Create `models/services/gym_service.py`:

```python
import sqlite3
from datetime import datetime
from flask_login import current_user

class GymService:
    def __init__(self):
        self.db_path = 'database.db'

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def get_all_exercises(self):
        """Get all exercises from database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM exercises ORDER BY name')
        exercises = cursor.fetchall()
        conn.close()
        return exercises

    def add_exercise(self, name, muscle_group=None):
        """Add a new exercise"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO exercises (name, muscle_group) VALUES (?, ?)',
            (name, muscle_group)
        )
        conn.commit()
        conn.close()

    def start_workout_session(self, notes=None):
        """Start a new workout session"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO workout_sessions (user_id, date, notes) VALUES (?, ?, ?)',
            (current_user.id, datetime.now().date(), notes)
        )
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return session_id

    def log_set(self, session_id, exercise_id, set_number, weight, reps):
        """Log a single set"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO workout_sets (session_id, exercise_id, set_number, weight, reps) VALUES (?, ?, ?, ?, ?)',
            (session_id, exercise_id, set_number, weight, reps)
        )
        conn.commit()
        conn.close()

    def get_user_workouts(self, limit=10):
        """Get user's recent workouts"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ws.*, COUNT(DISTINCT wset.exercise_id) as exercise_count
            FROM workout_sessions ws
            LEFT JOIN workout_sets wset ON ws.id = wset.session_id
            WHERE ws.user_id = ?
            GROUP BY ws.id
            ORDER BY ws.date DESC
            LIMIT ?
        ''', (current_user.id, limit))
        workouts = cursor.fetchall()
        conn.close()
        return workouts
```

### 3. Gym Blueprint
Create `models/blueprints/gym_bp.py`:

```python
from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from flask_login import login_required
from models.services.gym_service import GymService

gym_bp = Blueprint('gym', __name__, url_prefix='/gym')
gym_service = GymService()

@gym_bp.route('/')
@login_required
def dashboard():
    """Gym tracker dashboard"""
    recent_workouts = gym_service.get_user_workouts(5)
    return render_template('gym/dashboard.html', workouts=recent_workouts)

@gym_bp.route('/exercises')
@login_required
def exercises():
    """List all exercises"""
    exercises = gym_service.get_all_exercises()
    return render_template('gym/exercises/list.html', exercises=exercises)

@gym_bp.route('/exercises/add', methods=['GET', 'POST'])
@login_required
def add_exercise():
    """Add new exercise"""
    if request.method == 'POST':
        name = request.form.get('name')
        muscle_group = request.form.get('muscle_group')
        gym_service.add_exercise(name, muscle_group)
        return redirect(url_for('gym.exercises'))
    return render_template('gym/exercises/add.html')

@gym_bp.route('/workout/start')
@login_required
def start_workout():
    """Start a new workout session"""
    exercises = gym_service.get_all_exercises()
    return render_template('gym/workouts/log.html', exercises=exercises)

@gym_bp.route('/workout/log', methods=['POST'])
@login_required
def log_workout():
    """Log workout sets"""
    data = request.json
    session_id = data.get('session_id')

    if not session_id:
        # Create new session
        session_id = gym_service.start_workout_session()

    # Log the set
    gym_service.log_set(
        session_id,
        data['exercise_id'],
        data['set_number'],
        data['weight'],
        data['reps']
    )

    return jsonify({'success': True, 'session_id': session_id})

@gym_bp.route('/history')
@login_required
def history():
    """View workout history"""
    workouts = gym_service.get_user_workouts(20)
    return render_template('gym/history/list.html', workouts=workouts)
```

### 4. Basic HTML Template Example
Create `templates/gym/workouts/log.html`:

```html
{% extends "base.html" %}
{% block content %}
<div class="container mt-4">
    <h2>Log Workout</h2>

    <div id="workout-log">
        <div class="mb-3">
            <select id="exercise-select" class="form-control">
                <option value="">Select Exercise</option>
                {% for exercise in exercises %}
                <option value="{{ exercise[0] }}">{{ exercise[1] }}</option>
                {% endfor %}
            </select>
        </div>

        <div id="sets-container"></div>

        <button id="add-set" class="btn btn-primary">Add Set</button>
        <button id="finish-workout" class="btn btn-success">Finish Workout</button>
    </div>
</div>

<script>
let sessionId = null;
let setNumber = 1;

document.getElementById('add-set').addEventListener('click', function() {
    const exerciseId = document.getElementById('exercise-select').value;
    if (!exerciseId) {
        alert('Please select an exercise');
        return;
    }

    const setDiv = document.createElement('div');
    setDiv.className = 'mb-2';
    setDiv.innerHTML = `
        <div class="row">
            <div class="col">
                <input type="number" class="form-control weight-input" placeholder="Weight (kg)">
            </div>
            <div class="col">
                <input type="number" class="form-control reps-input" placeholder="Reps">
            </div>
            <div class="col">
                <button class="btn btn-sm btn-primary log-set">Log Set ${setNumber}</button>
            </div>
        </div>
    `;

    document.getElementById('sets-container').appendChild(setDiv);

    setDiv.querySelector('.log-set').addEventListener('click', function() {
        const weight = setDiv.querySelector('.weight-input').value;
        const reps = setDiv.querySelector('.reps-input').value;

        fetch('/gym/workout/log', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                session_id: sessionId,
                exercise_id: exerciseId,
                set_number: setNumber,
                weight: parseFloat(weight),
                reps: parseInt(reps)
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                sessionId = data.session_id;
                setNumber++;
                this.textContent = 'Logged!';
                this.disabled = true;
            }
        });
    });
});
</script>
{% endblock %}
```

### 5. Update app.py
Add to your app.py imports and blueprint registration:

```python
# Add to imports
from models.blueprints.gym_bp import gym_bp

# Add to blueprint registration section
app.register_blueprint(gym_bp)
```

## Running the Implementation

1. Run the migration script:
   ```bash
   python migrate_add_gym_tracker.py
   ```

2. Create the necessary directories:
   ```bash
   mkdir -p templates/gym/exercises
   mkdir -p templates/gym/workouts
   mkdir -p templates/gym/history
   mkdir -p models/services
   ```

3. Add navigation link in your base template:
   ```html
   <a href="{{ url_for('gym.dashboard') }}">Gym Tracker</a>
   ```

4. Test the basic functionality:
   - Add exercises at `/gym/exercises/add`
   - Start logging workout at `/gym/workout/start`
   - View history at `/gym/history`

This implementation provides the basic functionality requested:
- Add exercise names
- Log workouts with exercises, sets, reps, and loads
- View workout history

The structure follows your existing app patterns and can be easily extended with more features.
