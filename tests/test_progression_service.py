"""
Comprehensive Test Suite for Progression System
Implements testing guidelines as per PROGRESSION_DASHBOARD_IMPROVEMENTS.md
"""

import unittest
import sqlite3
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Import the services to test
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from models.services.progression_service import ProgressionService, ProgressionServiceError
from models.services.advanced_progression_service import AdvancedProgressionService
from models.services.progression_config import ProgressionConfig, get_development_config

class TestProgressionService(unittest.TestCase):
    """Test cases for ProgressionService"""

    def setUp(self):
        """Set up test database and service instance"""
        # Create temporary database
        self.db_fd, self.db_path = tempfile.mkstemp()

        # Use development config for testing
        self.config = get_development_config()
        self.service = ProgressionService(db_path=self.db_path, config=self.config)

        # Initialize test database
        self._init_test_database()
        self._create_test_data()

    def tearDown(self):
        """Clean up test database"""
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def _init_test_database(self):
        """Initialize test database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create required tables
        cursor.execute('''
            CREATE TABLE exercises (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                muscle_group TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE workout_sessions (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                date DATE NOT NULL,
                status TEXT DEFAULT 'in_progress'
            )
        ''')

        cursor.execute('''
            CREATE TABLE workout_sets (
                id INTEGER PRIMARY KEY,
                session_id INTEGER NOT NULL,
                exercise_id INTEGER NOT NULL,
                set_number INTEGER NOT NULL,
                weight REAL NOT NULL,
                reps INTEGER NOT NULL,
                rpe INTEGER,
                form_quality INTEGER,
                FOREIGN KEY (session_id) REFERENCES workout_sessions(id),
                FOREIGN KEY (exercise_id) REFERENCES exercises(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE user_gym_preferences (
                user_id INTEGER PRIMARY KEY,
                progression_strategy TEXT DEFAULT 'reps_first',
                min_reps_target INTEGER DEFAULT 10,
                max_reps_target INTEGER DEFAULT 15,
                weight_increment_upper REAL DEFAULT 2.5,
                weight_increment_lower REAL DEFAULT 5.0,
                rest_timer_enabled BOOLEAN DEFAULT 1,
                progression_notification_enabled BOOLEAN DEFAULT 1,
                progression_priority_1 TEXT DEFAULT 'reps',
                progression_priority_2 TEXT DEFAULT 'weight',
                progression_priority_3 TEXT DEFAULT 'volume',
                progression_priority_4 TEXT DEFAULT 'sets',
                progression_priority_5 TEXT DEFAULT 'exercises',
                pyramid_preference TEXT DEFAULT 'auto_detect'
            )
        ''')

        cursor.execute('''
            CREATE TABLE progression_history (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                exercise_id INTEGER NOT NULL,
                progression_date DATE NOT NULL,
                old_weight REAL,
                new_weight REAL,
                progression_type TEXT,
                notes TEXT,
                FOREIGN KEY (exercise_id) REFERENCES exercises(id)
            )
        ''')

        conn.commit()
        conn.close()

    def _create_test_data(self):
        """Create test data for progression analysis"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create test exercises
        cursor.execute("INSERT INTO exercises (id, name, muscle_group) VALUES (1, 'Bench Press', 'Chest')")
        cursor.execute("INSERT INTO exercises (id, name, muscle_group) VALUES (2, 'Squat', 'Legs')")
        cursor.execute("INSERT INTO exercises (id, name, muscle_group) VALUES (3, 'Deadlift', 'Back')")

        # Create test user preferences
        cursor.execute('''
            INSERT INTO user_gym_preferences (user_id, min_reps_target, max_reps_target)
            VALUES (1, 10, 15)
        ''')

        conn.commit()
        conn.close()

    def _create_ascending_workout_data(self, user_id: int, exercise_id: int):
        """Create test data with ascending pattern (40kg→50kg→60kg)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create 3 workouts with ascending pattern
        for i in range(3):
            workout_date = (datetime.now() - timedelta(days=i*2)).strftime('%Y-%m-%d')
            cursor.execute('''
                INSERT INTO workout_sessions (id, user_id, date, status)
                VALUES (?, ?, ?, 'completed')
            ''', (i+1, user_id, workout_date))

            # Create sets with ascending weights
            weights = [40, 50, 60]
            reps = [12, 10, 8]

            for set_num, (weight, rep) in enumerate(zip(weights, reps), 1):
                cursor.execute('''
                    INSERT INTO workout_sets (session_id, exercise_id, set_number, weight, reps)
                    VALUES (?, ?, ?, ?, ?)
                ''', (i+1, exercise_id, set_num, weight, rep))

        conn.commit()
        conn.close()

    def _create_straight_sets_data(self, user_id: int, exercise_id: int):
        """Create test data with straight sets pattern (50kg×3 sets)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create 3 workouts with straight sets
        for i in range(3):
            workout_date = (datetime.now() - timedelta(days=i*2)).strftime('%Y-%m-%d')
            cursor.execute('''
                INSERT INTO workout_sessions (id, user_id, date, status)
                VALUES (?, ?, ?, 'completed')
            ''', (i+10, user_id, workout_date))

            # Create sets with same weight
            for set_num in range(1, 4):
                cursor.execute('''
                    INSERT INTO workout_sets (session_id, exercise_id, set_number, weight, reps)
                    VALUES (?, ?, ?, ?, ?)
                ''', (i+10, exercise_id, set_num, 50, 10))

        conn.commit()
        conn.close()

    def test_user_data_validation_new_user(self):
        """Test validation for new users with no data"""
        result = self.service._validate_user_data(999)  # Non-existent user
        self.assertFalse(result)

    def test_user_data_validation_insufficient_workouts(self):
        """Test validation for users with insufficient workout data"""
        # Create user with only 1 workout (less than min_workouts=2 in dev config)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO workout_sessions (user_id, date, status)
            VALUES (1, '2024-01-01', 'completed')
        ''')
        conn.commit()
        conn.close()

        result = self.service._validate_user_data(1)
        self.assertFalse(result)

    def test_user_data_validation_sufficient_workouts(self):
        """Test validation for users with sufficient workout data"""
        # Create user with 3 workouts (meets min_workouts=2 in dev config)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        for i in range(3):
            cursor.execute('''
                INSERT INTO workout_sessions (user_id, date, status)
                VALUES (1, ?, 'completed')
            ''', (f'2024-01-0{i+1}',))
        conn.commit()
        conn.close()

        result = self.service._validate_user_data(1)
        self.assertTrue(result)

    def test_progression_data_validation_valid(self):
        """Test validation of valid progression data"""
        result = self.service._validate_progression_data(40.0, 42.5)
        self.assertTrue(result)

    def test_progression_data_validation_invalid_decrease(self):
        """Test validation rejects weight decreases"""
        result = self.service._validate_progression_data(50.0, 45.0)
        self.assertFalse(result)

    def test_progression_data_validation_invalid_jump(self):
        """Test validation rejects unrealistic weight jumps"""
        # 100% increase should be rejected (config allows 50% max)
        result = self.service._validate_progression_data(40.0, 80.0)
        self.assertFalse(result)

    def test_progression_data_validation_null_values(self):
        """Test validation rejects null values"""
        result = self.service._validate_progression_data(None, 42.5)
        self.assertFalse(result)

        result = self.service._validate_progression_data(40.0, None)
        self.assertFalse(result)

    def test_get_user_preferences_new_user(self):
        """Test getting preferences for new user returns defaults"""
        prefs = self.service.get_user_preferences(999)  # Non-existent user

        self.assertEqual(prefs['progression_strategy'], 'reps_first')
        self.assertEqual(prefs['min_reps_target'], 10)
        self.assertEqual(prefs['max_reps_target'], 15)
        self.assertEqual(prefs['weight_increment_upper'], 2.5)

    def test_get_user_preferences_existing_user(self):
        """Test getting preferences for existing user"""
        prefs = self.service.get_user_preferences(1)

        self.assertEqual(prefs['min_reps_target'], 10)
        self.assertEqual(prefs['max_reps_target'], 15)

    def test_check_progression_readiness_new_user(self):
        """Test progression readiness for new user"""
        result = self.service.check_progression_readiness(999, 1)

        self.assertFalse(result['ready'])
        self.assertEqual(result['user_state'], 'new_user')
        self.assertIn('complete at least 3 workouts', result['reason'])

    def test_check_progression_readiness_minimal_data(self):
        """Test progression readiness with minimal data"""
        # Create user with sufficient workouts but no exercise data
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        for i in range(3):
            cursor.execute('''
                INSERT INTO workout_sessions (user_id, date, status)
                VALUES (1, ?, 'completed')
            ''', (f'2024-01-0{i+1}',))
        conn.commit()
        conn.close()

        result = self.service.check_progression_readiness(1, 1)

        self.assertFalse(result['ready'])
        self.assertEqual(result['user_state'], 'minimal_data')

    def test_record_progression_valid(self):
        """Test recording valid progression"""
        # Create sufficient workout data first
        self._create_ascending_workout_data(1, 1)

        result = self.service.record_progression(1, 1, 40.0, 42.5, 'weight_increase')
        self.assertTrue(result)

        # Verify progression was recorded
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM progression_history WHERE user_id = 1')
        count = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(count, 1)

    def test_record_progression_invalid_data(self):
        """Test recording progression with invalid data"""
        result = self.service.record_progression(1, 1, 50.0, 45.0)  # Weight decrease
        self.assertFalse(result)

    def test_record_progression_nonexistent_exercise(self):
        """Test recording progression for non-existent exercise"""
        # Create sufficient workout data first
        self._create_ascending_workout_data(1, 1)

        result = self.service.record_progression(1, 999, 40.0, 42.5)  # Non-existent exercise
        self.assertFalse(result)

    def test_get_progression_suggestions_new_user(self):
        """Test progression suggestions for new user"""
        suggestions = self.service.get_progression_suggestions(999)

        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0]['user_state'], 'new_user')
        self.assertFalse(suggestions[0]['ready'])

    def test_get_progression_suggestions_no_exercises(self):
        """Test progression suggestions for user with no exercises"""
        # Create user with workouts but no exercise data
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        for i in range(3):
            cursor.execute('''
                INSERT INTO workout_sessions (user_id, date, status)
                VALUES (1, ?, 'completed')
            ''', (f'2024-01-0{i+1}',))
        conn.commit()
        conn.close()

        suggestions = self.service.get_progression_suggestions(1)

        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0]['user_state'], 'no_exercises')

    def test_cleanup_orphaned_records(self):
        """Test cleanup of orphaned workout_sets"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create orphaned workout_sets (session_id doesn't exist)
        cursor.execute('''
            INSERT INTO workout_sets (session_id, exercise_id, set_number, weight, reps)
            VALUES (999, 1, 1, 40, 10)
        ''')
        cursor.execute('''
            INSERT INTO workout_sets (session_id, exercise_id, set_number, weight, reps)
            VALUES (998, 1, 1, 40, 10)
        ''')
        conn.commit()
        conn.close()

        result = self.service._cleanup_orphaned_records(1)
        self.assertEqual(result['cleaned_records'], 2)

    def test_exercise_performance_history_invalid_exercise(self):
        """Test getting performance history for invalid exercise"""
        history = self.service.get_exercise_performance_history(1, -1)  # Invalid exercise_id
        self.assertEqual(len(history), 0)

    def test_exercise_performance_history_no_data(self):
        """Test getting performance history with no data"""
        # Create sufficient workouts but no sets
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        for i in range(3):
            cursor.execute('''
                INSERT INTO workout_sessions (user_id, date, status)
                VALUES (1, ?, 'completed')
            ''', (f'2024-01-0{i+1}',))
        conn.commit()
        conn.close()

        history = self.service.get_exercise_performance_history(1, 1)
        self.assertEqual(len(history), 0)


class TestAdvancedProgressionService(unittest.TestCase):
    """Test cases for AdvancedProgressionService"""

    def setUp(self):
        """Set up test database and service instance"""
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.service = AdvancedProgressionService(db_path=self.db_path)
        self._init_test_database()

    def tearDown(self):
        """Clean up test database"""
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def _init_test_database(self):
        """Initialize test database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create required tables (simplified for testing)
        cursor.execute('''
            CREATE TABLE exercises (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                muscle_group TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE workout_sessions (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                date DATE NOT NULL,
                status TEXT DEFAULT 'completed'
            )
        ''')

        cursor.execute('''
            CREATE TABLE workout_sets (
                id INTEGER PRIMARY KEY,
                session_id INTEGER NOT NULL,
                exercise_id INTEGER NOT NULL,
                set_number INTEGER NOT NULL,
                weight REAL NOT NULL,
                reps INTEGER NOT NULL,
                FOREIGN KEY (session_id) REFERENCES workout_sessions(id),
                FOREIGN KEY (exercise_id) REFERENCES exercises(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE user_gym_preferences (
                user_id INTEGER PRIMARY KEY,
                min_reps_target INTEGER DEFAULT 10,
                max_reps_target INTEGER DEFAULT 15,
                weight_increment_upper REAL DEFAULT 2.5,
                weight_increment_lower REAL DEFAULT 5.0
            )
        ''')

        # Create test data
        cursor.execute("INSERT INTO exercises (id, name, muscle_group) VALUES (1, 'Bench Press', 'Chest')")
        cursor.execute("INSERT INTO user_gym_preferences (user_id) VALUES (1)")

        conn.commit()
        conn.close()

    def test_pattern_detection_ascending(self):
        """Test pattern detection for ascending pyramid"""
        # Create test data with ascending pattern
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create workout with ascending weights
        cursor.execute('''
            INSERT INTO workout_sessions (id, user_id, date, status)
            VALUES (1, 1, '2024-01-01', 'completed')
        ''')

        weights = [40, 50, 60]
        for i, weight in enumerate(weights, 1):
            cursor.execute('''
                INSERT INTO workout_sets (session_id, exercise_id, set_number, weight, reps)
                VALUES (1, 1, ?, ?, 10)
            ''', (i, weight))

        conn.commit()
        conn.close()

        pattern = self.service.detect_pyramid_pattern(1, 1)

        self.assertEqual(pattern['pattern'], 'ascending')
        self.assertGreater(pattern['confidence'], 0)

    def test_pattern_detection_straight(self):
        """Test pattern detection for straight sets"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create workout with same weights
        cursor.execute('''
            INSERT INTO workout_sessions (id, user_id, date, status)
            VALUES (1, 1, '2024-01-01', 'completed')
        ''')

        for i in range(1, 4):
            cursor.execute('''
                INSERT INTO workout_sets (session_id, exercise_id, set_number, weight, reps)
                VALUES (1, 1, ?, 50, 10)
            ''', (i,))

        conn.commit()
        conn.close()

        pattern = self.service.detect_pyramid_pattern(1, 1)

        self.assertEqual(pattern['pattern'], 'straight')

    def test_pattern_detection_no_data(self):
        """Test pattern detection with no data"""
        pattern = self.service.detect_pyramid_pattern(1, 1)

        self.assertEqual(pattern['pattern'], 'unknown')
        self.assertEqual(pattern['confidence'], 0.0)

    def test_volume_calculation_accuracy(self):
        """Test volume calculation accuracy with known data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create workout with known volume: 40×12 + 50×10 + 60×8 = 1460
        cursor.execute('''
            INSERT INTO workout_sessions (id, user_id, date, status)
            VALUES (1, 1, '2024-01-01', 'completed')
        ''')

        sets_data = [(40, 12), (50, 10), (60, 8)]
        for i, (weight, reps) in enumerate(sets_data, 1):
            cursor.execute('''
                INSERT INTO workout_sets (session_id, exercise_id, set_number, weight, reps)
                VALUES (1, 1, ?, ?, ?)
            ''', (i, weight, reps))

        conn.commit()
        conn.close()

        # Create volume tracking table for testing
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE workout_volume_tracking (
                id INTEGER PRIMARY KEY,
                workout_id INTEGER NOT NULL,
                exercise_id INTEGER NOT NULL,
                total_volume REAL,
                total_reps INTEGER,
                total_sets INTEGER,
                avg_intensity REAL
            )
        ''')
        conn.commit()
        conn.close()

        result = self.service.calculate_volume_metrics(1, 1)

        expected_volume = 40*12 + 50*10 + 60*8  # 1460
        self.assertEqual(result['total_volume'], expected_volume)
        self.assertEqual(result['total_reps'], 30)
        self.assertEqual(result['total_sets'], 3)
        self.assertEqual(result['avg_intensity'], 50.0)


class TestProgressionConfig(unittest.TestCase):
    """Test cases for ProgressionConfig"""

    def setUp(self):
        """Set up test config"""
        self.config = ProgressionConfig()

    def test_default_configuration_values(self):
        """Test that default configuration values are reasonable"""
        self.assertGreaterEqual(self.config.pattern_detection.min_workouts, 2)
        self.assertGreater(self.config.pattern_detection.confidence_threshold, 0.5)
        self.assertLessEqual(self.config.pattern_detection.confidence_threshold, 1.0)

        self.assertGreater(self.config.volume_tracking.default_window_days, 0)
        self.assertGreater(self.config.progression_thresholds.ready_consecutive_workouts, 1)

    def test_config_validation_valid(self):
        """Test configuration validation with valid values"""
        validation = self.config.validate_config()

        self.assertTrue(validation['valid'])
        self.assertEqual(len(validation['issues']), 0)

    def test_config_validation_invalid_min_workouts(self):
        """Test configuration validation with invalid min_workouts"""
        self.config.pattern_detection.min_workouts = 1  # Too low

        validation = self.config.validate_config()

        self.assertFalse(validation['valid'])
        self.assertGreater(len(validation['issues']), 0)

    def test_config_validation_invalid_rep_targets(self):
        """Test configuration validation with invalid rep targets"""
        self.config.default_user_preferences.min_reps_target = 15
        self.config.default_user_preferences.max_reps_target = 10  # min > max

        validation = self.config.validate_config()

        self.assertFalse(validation['valid'])
        self.assertIn('min_reps_target must be less than max_reps_target', validation['issues'])

    def test_development_config(self):
        """Test development configuration has appropriate values"""
        dev_config = get_development_config()

        # Development should have more lenient thresholds
        self.assertLessEqual(dev_config.pattern_detection.min_workouts, 3)
        self.assertLessEqual(dev_config.pattern_detection.confidence_threshold, 0.7)
        self.assertLessEqual(dev_config.progression_thresholds.ready_consecutive_workouts, 3)


class TestIntegrationScenarios(unittest.TestCase):
    """Integration test scenarios"""

    def setUp(self):
        """Set up test environment"""
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.config = get_development_config()
        self.progression_service = ProgressionService(db_path=self.db_path, config=self.config)
        self.advanced_service = AdvancedProgressionService(db_path=self.db_path)

        self._init_test_database()

    def tearDown(self):
        """Clean up test environment"""
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def _init_test_database(self):
        """Initialize complete test database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create all required tables
        cursor.execute('''
            CREATE TABLE exercises (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                muscle_group TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE workout_sessions (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                date DATE NOT NULL,
                status TEXT DEFAULT 'completed'
            )
        ''')

        cursor.execute('''
            CREATE TABLE workout_sets (
                id INTEGER PRIMARY KEY,
                session_id INTEGER NOT NULL,
                exercise_id INTEGER NOT NULL,
                set_number INTEGER NOT NULL,
                weight REAL NOT NULL,
                reps INTEGER NOT NULL,
                rpe INTEGER,
                form_quality INTEGER,
                FOREIGN KEY (session_id) REFERENCES workout_sessions(id),
                FOREIGN KEY (exercise_id) REFERENCES exercises(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE user_gym_preferences (
                user_id INTEGER PRIMARY KEY,
                progression_strategy TEXT DEFAULT 'reps_first',
                min_reps_target INTEGER DEFAULT 10,
                max_reps_target INTEGER DEFAULT 15,
                weight_increment_upper REAL DEFAULT 2.5,
                weight_increment_lower REAL DEFAULT 5.0,
                rest_timer_enabled BOOLEAN DEFAULT 1,
                progression_notification_enabled BOOLEAN DEFAULT 1,
                progression_priority_1 TEXT DEFAULT 'reps',
                progression_priority_2 TEXT DEFAULT 'weight',
                progression_priority_3 TEXT DEFAULT 'volume',
                progression_priority_4 TEXT DEFAULT 'sets',
                progression_priority_5 TEXT DEFAULT 'exercises',
                pyramid_preference TEXT DEFAULT 'auto_detect'
            )
        ''')

        cursor.execute('''
            CREATE TABLE progression_history (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                exercise_id INTEGER NOT NULL,
                progression_date DATE NOT NULL,
                old_weight REAL,
                new_weight REAL,
                progression_type TEXT,
                notes TEXT,
                FOREIGN KEY (exercise_id) REFERENCES exercises(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE workout_volume_tracking (
                id INTEGER PRIMARY KEY,
                workout_id INTEGER NOT NULL,
                exercise_id INTEGER NOT NULL,
                total_volume REAL,
                total_reps INTEGER,
                total_sets INTEGER,
                avg_intensity REAL
            )
        ''')

        # Create test data
        cursor.execute("INSERT INTO exercises (id, name, muscle_group) VALUES (1, 'Bench Press', 'Chest')")
        cursor.execute("INSERT INTO user_gym_preferences (user_id) VALUES (1)")

        conn.commit()
        conn.close()

    def test_new_user_journey(self):
        """Test complete new user journey: Empty state → First workout → Pattern emergence"""
        user_id = 1
        exercise_id = 1

        # Step 1: New user - should get encouraging message
        suggestions = self.progression_service.get_progression_suggestions(user_id)
        self.assertEqual(suggestions[0]['user_state'], 'new_user')
        self.assertIn('complete at least', suggestions[0]['reason'].lower())

        # Step 2: Add first workout
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO workout_sessions (id, user_id, date, status)
            VALUES (1, ?, '2024-01-01', 'completed')
        ''', (user_id,))

        # Add sets
        for i in range(1, 4):
            cursor.execute('''
                INSERT INTO workout_sets (session_id, exercise_id, set_number, weight, reps)
                VALUES (1, ?, ?, 40, 10)
            ''', (exercise_id, i))

        conn.commit()
        conn.close()

        # Still insufficient data (only 1 workout, need 2+ for dev config)
        readiness = self.progression_service.check_progression_readiness(user_id, exercise_id)
        self.assertEqual(readiness['user_state'], 'new_user')

        # Step 3: Add second workout
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO workout_sessions (id, user_id, date, status)
            VALUES (2, ?, '2024-01-03', 'completed')
        ''', (user_id,))

        for i in range(1, 4):
            cursor.execute('''
                INSERT INTO workout_sets (session_id, exercise_id, set_number, weight, reps)
                VALUES (2, ?, ?, 40, 12)
            ''', (exercise_id, i))

        conn.commit()
        conn.close()

        # Now should have progression analysis (2 workouts = sufficient data)
        readiness = self.progression_service.check_progression_readiness(user_id, exercise_id)
        self.assertFalse(readiness.get('ready', False))  # Not ready yet, but has valid analysis
        self.assertIn('suggestion', readiness)  # Should have progression suggestions

        # Step 4: Pattern should emerge
        pattern = self.advanced_service.detect_pyramid_pattern(user_id, exercise_id)
        self.assertEqual(pattern['pattern'], 'straight')  # Same weight across sets

    def test_progression_acceptance_flow(self):
        """Test progression acceptance flow: Ready → Accept → Record"""
        user_id = 1
        exercise_id = 1

        # Create workout history that should trigger progression readiness
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create 3 workouts hitting max reps (15)
        for workout_num in range(1, 4):
            cursor.execute('''
                INSERT INTO workout_sessions (id, user_id, date, status)
                VALUES (?, ?, ?, 'completed')
            ''', (workout_num, user_id, f'2024-01-0{workout_num}'))

            for set_num in range(1, 4):
                cursor.execute('''
                    INSERT INTO workout_sets (session_id, exercise_id, set_number, weight, reps)
                    VALUES (?, ?, ?, 40, 15)
                ''', (workout_num, exercise_id, set_num))

        conn.commit()
        conn.close()

        # Check readiness
        readiness = self.progression_service.check_progression_readiness(user_id, exercise_id)
        self.assertTrue(readiness.get('ready', False))
        self.assertEqual(readiness.get('suggestion'), 'increase_weight')

        # Accept progression
        old_weight = readiness.get('current_weight', 40)
        new_weight = readiness.get('new_weight', 42.5)

        success = self.progression_service.record_progression(
            user_id, exercise_id, old_weight, new_weight, 'weight_increase'
        )
        self.assertTrue(success)

        # Verify progression was recorded
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM progression_history
            WHERE user_id = ? AND exercise_id = ?
        ''', (user_id, exercise_id))
        count = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(count, 1)


if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestSuite()

    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestProgressionService))
    test_suite.addTest(unittest.makeSuite(TestAdvancedProgressionService))
    test_suite.addTest(unittest.makeSuite(TestProgressionConfig))
    test_suite.addTest(unittest.makeSuite(TestIntegrationScenarios))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # Print summary
    print(f"\n{'='*50}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    print(f"{'='*50}")
