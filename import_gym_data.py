import csv
import sqlite3
from datetime import datetime

def parse_date(date_str):
    """Parse date from CSV format to Python date"""
    try:
        # Handle format like "20.7.23"
        return datetime.strptime(date_str, "%d.%m.%y").date()
    except:
        return None

def parse_loads_reps(loads_str, reps_str):
    """Parse comma-separated loads and reps"""
    try:
        loads = [float(x.strip()) for x in loads_str.split(',') if x.strip()]
        reps = [int(x.strip()) for x in reps_str.split(',') if x.strip()]
        return list(zip(loads, reps))
    except:
        return []

def import_csv_data(csv_file='data/GYM Tracker - Gym Tracker.csv'):
    """Import workout data from CSV file"""
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Create a mapping for exercises
    exercise_map = {}

    # Statistics
    workouts_created = 0
    sets_imported = 0
    exercises_added = 0

    with open(csv_file, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader)  # Skip header

        current_date = None
        current_session_id = None
        workout_notes = None

        for i, row in enumerate(reader):
            if len(row) < 7:
                continue



            # Parse row data - adjusted for actual CSV format
            row_num = row[0].strip()
            date_str = row[1].strip()

            # Check if this is a date row (has date and 'sets' in col3)
            if date_str:
                col3 = row[3].strip() if len(row) > 3 else ""
                if col3.lower() == 'sets':
                    parsed_date = parse_date(date_str)
                    if parsed_date:
                        current_date = parsed_date
                        week_training = row[2].strip()
                        # Create new session for new date
                        notes = f'Imported from CSV - {week_training}'
                        if len(row) > 12 and row[12]:  # Comments column
                            notes += f' - {row[12]}'

                        cursor.execute(
                            'INSERT INTO workout_sessions (user_id, date, notes) VALUES (?, ?, ?)',
                            (1, current_date, notes)
                        )
                        current_session_id = cursor.lastrowid
                        workouts_created += 1
                    continue

            # For exercise rows (no date), the exercise name is in column 2
            col2 = row[2].strip() if len(row) > 2 else ""

            # Skip total rows or empty rows
            if not col2 or col2.lower() in ['total', '']:
                continue

            # Skip if no current session
            if not current_session_id:
                continue

            # If we get here, col2 should be an exercise name
            exercise_name = col2

            # Parse loads and reps from columns 4 and 5
            loads_str = row[4].strip() if len(row) > 4 else ""
            reps_str = row[5].strip() if len(row) > 5 else ""



            # Clean exercise name
            exercise_name = exercise_name.strip()

            # Map common variations to standard names
            exercise_variations = {
                'inline bench': 'Incline Bench Press',
                'inc. b. dumbels': 'Incline Dumbbell Press',
                'inc. b. barbel': 'Incline Barbell Press',
                'barbel curls': 'Barbell Curls',
                'dumbel press': 'Dumbbell Press',
                'cc abs': 'Abs',
                'calves': 'Calves',
                'leg hack': 'Hack Squat',
                'seatted leg curls': 'Seated Leg Curls',
                'preachers curls': 'Preacher Curls',
                'preachers barbell curls': 'Preacher Barbell Curls'
            }

            # Normalize exercise name
            exercise_name_lower = exercise_name.lower()
            for variation, standard in exercise_variations.items():
                if variation in exercise_name_lower:
                    exercise_name = standard
                    break

            # Get or create exercise
            if exercise_name not in exercise_map:
                # Check if exercise exists
                cursor.execute('SELECT id FROM exercises WHERE LOWER(name) = LOWER(?)', (exercise_name,))
                result = cursor.fetchone()

                if result:
                    exercise_map[exercise_name] = result[0]
                else:
                    # Determine muscle group based on exercise name
                    muscle_group = None
                    if any(x in exercise_name.lower() for x in ['squat', 'leg', 'calves', 'hack']):
                        muscle_group = 'Legs'
                    elif any(x in exercise_name.lower() for x in ['bench', 'press', 'fly', 'chest']):
                        muscle_group = 'Chest'
                    elif any(x in exercise_name.lower() for x in ['pull', 'row', 'deadlift', 'lat']):
                        muscle_group = 'Back'
                    elif any(x in exercise_name.lower() for x in ['curl', 'bicep', 'preacher']):
                        muscle_group = 'Biceps'
                    elif any(x in exercise_name.lower() for x in ['pushdown', 'tricep', 'french']):
                        muscle_group = 'Triceps'
                    elif any(x in exercise_name.lower() for x in ['shoulder', 'lateral', 'overhead']):
                        muscle_group = 'Shoulders'
                    elif any(x in exercise_name.lower() for x in ['abs', 'core']):
                        muscle_group = 'Core'

                                        # Insert new exercise
                    cursor.execute('INSERT INTO exercises (name, muscle_group) VALUES (?, ?)',
                                 (exercise_name, muscle_group))
                    exercise_map[exercise_name] = cursor.lastrowid
                    exercises_added += 1

            exercise_id = exercise_map[exercise_name]

            # Parse and insert sets
            sets_data = parse_loads_reps(loads_str, reps_str)
            for set_num, (weight, reps) in enumerate(sets_data, 1):
                cursor.execute(
                    'INSERT INTO workout_sets (session_id, exercise_id, set_number, weight, reps) VALUES (?, ?, ?, ?, ?)',
                    (current_session_id, exercise_id, set_num, weight, reps)
                )
                sets_imported += 1

    conn.commit()
    conn.close()

    print(f"\nImport completed!")
    print(f"Workouts created: {workouts_created}")
    print(f"Exercises in database: {len(exercise_map)}")
    print(f"New exercises added: {exercises_added}")
    print(f"Sets imported: {sets_imported}")

if __name__ == '__main__':
    # Make sure gym tracker tables exist first
    print("Importing workout data from CSV...")
    import_csv_data()
    print("\nImport finished!")
