"""
Comprehensive tests for Medium Priority Features
Tests enhanced UX, advanced algorithms, security, and monitoring features
"""

import unittest
import tempfile
import os
import sqlite3
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Import the services we're testing
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.services.advanced_progression_service import (
    AdvancedProgressionService, PatternType, PatternAnalysis,
    ReadinessFactors, SmartSuggestion
)
from models.services.security_service import (
    SecurityService, AccessLevel, AuditAction, SecurityError
)
from models.services.monitoring_service import (
    MonitoringService, MetricType, AlertSeverity, HealthStatus
)


class TestAdvancedProgressionService(unittest.TestCase):
    """Test advanced progression algorithms and pattern detection"""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name

        # Initialize database with test schema
        self._init_test_database()

        self.service = AdvancedProgressionService(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def _init_test_database(self):
        """Initialize test database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Create required tables
            cursor.execute("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    username TEXT UNIQUE,
                    email TEXT,
                    role TEXT DEFAULT 'user'
                )
            """)

            cursor.execute("""
                CREATE TABLE exercises (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    muscle_group TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE workout_sessions (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    exercise_id INTEGER,
                    date TEXT,
                    status TEXT DEFAULT 'completed',
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (exercise_id) REFERENCES exercises(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE workout_sets (
                    id INTEGER PRIMARY KEY,
                    session_id INTEGER,
                    exercise_id INTEGER,
                    set_number INTEGER,
                    weight REAL,
                    reps INTEGER,
                    rpe INTEGER,
                    form_quality INTEGER,
                    FOREIGN KEY (session_id) REFERENCES workout_sessions(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE progression_history (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    exercise_id INTEGER,
                    progression_date TEXT,
                    progression_type TEXT,
                    old_value REAL,
                    new_value REAL,
                    notes TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (exercise_id) REFERENCES exercises(id)
                )
            """)

            # Insert test data
            cursor.execute("INSERT INTO users (id, username, role) VALUES (1, 'testuser', 'user')")
            cursor.execute("INSERT INTO exercises (id, name, muscle_group) VALUES (1, 'Bench Press', 'Chest')")

            conn.commit()

    def _create_test_workout_data(self, pattern_type: str = 'ascending'):
        """Create test workout data with specific patterns"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Create 5 workouts with different patterns
            for i in range(5):
                workout_date = (datetime.now() - timedelta(days=i*3)).isoformat()
                cursor.execute("""
                    INSERT INTO workout_sessions (id, user_id, exercise_id, date, status)
                    VALUES (?, 1, 1, ?, 'completed')
                """, (i+1, workout_date))

                # Create sets based on pattern type
                if pattern_type == 'ascending':
                    sets_data = [(40, 12), (50, 10), (60, 8)]
                elif pattern_type == 'descending':
                    sets_data = [(60, 8), (50, 10), (40, 12)]
                elif pattern_type == 'straight':
                    sets_data = [(50, 10), (50, 10), (50, 10)]
                else:
                    sets_data = [(45, 10), (55, 8), (50, 9)]

                for j, (weight, reps) in enumerate(sets_data):
                    cursor.execute("""
                        INSERT INTO workout_sets
                        (session_id, exercise_id, set_number, weight, reps, rpe, form_quality)
                        VALUES (?, 1, ?, ?, ?, 7, 4)
                    """, (i+1, j+1, weight, reps))

            conn.commit()

    def test_advanced_pattern_detection_ascending(self):
        """Test detection of ascending (pyramid up) pattern"""
        self._create_test_workout_data('ascending')

        result = self.service.detect_advanced_pattern(user_id=1, exercise_id=1)

        self.assertIsInstance(result, PatternAnalysis)
        self.assertEqual(result.pattern, PatternType.ASCENDING)
        self.assertGreater(result.confidence, 0.8)
        self.assertGreater(result.consistency_score, 0.0)
        self.assertEqual(result.sample_size, 5)

    def test_advanced_pattern_detection_straight(self):
        """Test detection of straight sets pattern"""
        self._create_test_workout_data('straight')

        result = self.service.detect_advanced_pattern(user_id=1, exercise_id=1)

        self.assertEqual(result.pattern, PatternType.STRAIGHT)
        self.assertGreater(result.confidence, 0.8)

    def test_multi_factor_readiness_calculation(self):
        """Test multi-factor readiness analysis"""
        self._create_test_workout_data('ascending')

        result = self.service.calculate_multi_factor_readiness(user_id=1, exercise_id=1)

        self.assertIsInstance(result, ReadinessFactors)
        self.assertGreaterEqual(result.rep_achievement_score, 0.0)
        self.assertLessEqual(result.rep_achievement_score, 1.0)
        self.assertGreaterEqual(result.overall_readiness, 0.0)
        self.assertLessEqual(result.overall_readiness, 1.0)
        self.assertIsInstance(result.recommendation, str)

    def test_smart_suggestions_generation(self):
        """Test intelligent progression suggestions"""
        self._create_test_workout_data('ascending')

        # Add some progression history
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO progression_history
                (user_id, exercise_id, progression_date, progression_type, old_value, new_value)
                VALUES (1, 1, ?, 'weight', 50, 52.5)
            """, (datetime.now().isoformat(),))
            conn.commit()

        suggestions = self.service.generate_smart_suggestions(user_id=1, exercise_id=1)

        self.assertIsInstance(suggestions, list)
        if suggestions:
            suggestion = suggestions[0]
            self.assertIsInstance(suggestion, SmartSuggestion)
            self.assertIn(suggestion.suggestion_type, ['weight_increase', 'rep_increase', 'deload', 'plateau_break'])
            self.assertIsInstance(suggestion.reasoning, str)
            self.assertIsInstance(suggestion.alternative_options, list)

    def test_pattern_consistency_calculation(self):
        """Test pattern consistency across workouts"""
        self._create_test_workout_data('ascending')

        # Get workout history
        workout_history = self.service._get_workout_history(user_id=1, exercise_id=1, limit=5)

        consistency = self.service._calculate_pattern_consistency(workout_history, PatternType.ASCENDING)

        self.assertGreaterEqual(consistency, 0.0)
        self.assertLessEqual(consistency, 1.0)

    def test_insufficient_data_handling(self):
        """Test handling of insufficient workout data"""
        # Don't create any workout data

        result = self.service.detect_advanced_pattern(user_id=1, exercise_id=1)

        self.assertEqual(result.pattern, PatternType.UNKNOWN)
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.sample_size, 0)


class TestSecurityService(unittest.TestCase):
    """Test security and data access control features"""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name

        self.service = SecurityService(self.db_path)

        # Initialize test users
        self._init_test_users()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def _init_test_users(self):
        """Initialize test users"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT UNIQUE,
                    email TEXT,
                    role TEXT DEFAULT 'user'
                )
            """)

            cursor.execute("INSERT INTO users (id, username, role) VALUES (1, 'testuser', 'user')")
            cursor.execute("INSERT INTO users (id, username, role) VALUES (2, 'testcoach', 'coach')")
            cursor.execute("INSERT INTO users (id, username, role) VALUES (3, 'testadmin', 'admin')")

            conn.commit()

    def test_session_creation_and_validation(self):
        """Test session creation and validation"""
        # Create session
        session_token = self.service.create_session(
            user_id=1,
            ip_address='127.0.0.1',
            user_agent='Test Browser'
        )

        self.assertIsInstance(session_token, str)
        self.assertGreater(len(session_token), 20)

        # Validate session
        user_id = self.service.validate_session(session_token)
        self.assertEqual(user_id, 1)

        # Validate invalid session
        invalid_user_id = self.service.validate_session('invalid_token')
        self.assertIsNone(invalid_user_id)

    def test_session_invalidation(self):
        """Test session invalidation"""
        session_token = self.service.create_session(user_id=1)

        # Validate session exists
        user_id = self.service.validate_session(session_token)
        self.assertEqual(user_id, 1)

        # Invalidate session
        self.service.invalidate_session(session_token)

        # Validate session is now invalid
        user_id = self.service.validate_session(session_token)
        self.assertIsNone(user_id)

    def test_failed_login_tracking(self):
        """Test failed login attempt tracking"""
        username = 'testuser'
        ip_address = '127.0.0.1'

        # Record exactly the threshold number of failed attempts (5)
        for _ in range(5):
            self.service.record_failed_login(username, ip_address)

        # Check if account is now locked (should be at threshold)
        is_locked = self.service.is_account_locked(username, ip_address)
        self.assertTrue(is_locked)

        # Test that fewer attempts don't trigger lockout
        # Create a new service instance with fresh database for clean test
        temp_db2 = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db2.close()
        service2 = SecurityService(temp_db2.name)

        try:
            # Record 4 attempts (below threshold)
            for _ in range(4):
                service2.record_failed_login(username, ip_address)

            # Should not be locked
            is_locked2 = service2.is_account_locked(username, ip_address)
            self.assertFalse(is_locked2)
        finally:
            if os.path.exists(temp_db2.name):
                os.unlink(temp_db2.name)

    def test_permission_management(self):
        """Test permission granting and revoking"""
        user_id = 1
        permission_type = 'view_user_data'
        resource_id = 2
        granted_by = 3

        # Grant permission
        self.service.grant_permission(
            user_id=user_id,
            permission_type=permission_type,
            resource_type='user',
            resource_id=resource_id,
            granted_by=granted_by
        )

        # Check permission exists
        has_permission = self.service._has_permission(user_id, permission_type, resource_id)
        self.assertTrue(has_permission)

        # Revoke permission
        self.service.revoke_permission(
            user_id=user_id,
            permission_type=permission_type,
            resource_type='user',
            resource_id=resource_id,
            revoked_by=granted_by
        )

        # Check permission is revoked
        has_permission = self.service._has_permission(user_id, permission_type, resource_id)
        self.assertFalse(has_permission)

    def test_audit_trail_logging(self):
        """Test audit trail logging"""
        user_id = 1
        action = AuditAction.LOGIN
        details = {'session_created': True}

        # Log audit event
        self.service.log_audit_event(
            user_id=user_id,
            action=action,
            resource_type='session',
            details=details,
            ip_address='127.0.0.1'
        )

        # Retrieve audit trail
        audit_entries = self.service.get_audit_trail(user_id=user_id, limit=10)

        self.assertGreater(len(audit_entries), 0)
        entry = audit_entries[0]
        self.assertEqual(entry.user_id, user_id)
        self.assertEqual(entry.action, action)
        self.assertEqual(entry.details, details)

    def test_security_metrics(self):
        """Test security metrics collection"""
        # Create some test data
        self.service.create_session(user_id=1)
        self.service.record_failed_login('testuser', '127.0.0.1')
        self.service.log_audit_event(user_id=1, action=AuditAction.VIEW_DATA)

        metrics = self.service.get_security_metrics()

        self.assertIsInstance(metrics, dict)
        self.assertIn('active_sessions', metrics)
        self.assertIn('failed_logins_24h', metrics)
        self.assertIn('audit_events_24h', metrics)
        self.assertIn('security_policy', metrics)

    @patch('models.services.security_service.SecurityService._get_current_user_id')
    def test_access_control_decorator(self, mock_get_user_id):
        """Test access control decorator functionality"""
        mock_get_user_id.return_value = 1

        @self.service.require_user_access([AccessLevel.USER])
        def test_function(current_user_id=None):
            return f"Access granted to user {current_user_id}"

        # Should work with valid user
        result = test_function()
        self.assertIn("Access granted", result)

        # Should fail without user
        mock_get_user_id.return_value = None
        with self.assertRaises(SecurityError):
            test_function()


class TestMonitoringService(unittest.TestCase):
    """Test monitoring and observability features"""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name

        self.service = MonitoringService(self.db_path)

        # Give the background thread a moment to start
        import time
        time.sleep(0.1)

    def tearDown(self):
        self.service.shutdown()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_metric_recording(self):
        """Test metric recording and retrieval"""
        metric_name = 'test_metric'
        metric_value = 42.5

        # Record metric
        self.service.record_metric(
            name=metric_name,
            value=metric_value,
            metric_type=MetricType.GAUGE,
            tags={'environment': 'test'},
            unit='ms'
        )

        # Give background processing time to store
        import time
        time.sleep(1.5)

        # Retrieve metrics
        metrics = self.service.get_metrics(name=metric_name, limit=10)

        self.assertGreater(len(metrics), 0)
        metric = metrics[0]
        self.assertEqual(metric.name, metric_name)
        self.assertEqual(metric.value, metric_value)
        self.assertEqual(metric.type, MetricType.GAUGE)
        self.assertEqual(metric.unit, 'ms')

    def test_counter_increment(self):
        """Test counter metric incrementation"""
        counter_name = 'test_counter'

        # Increment counter multiple times
        for i in range(5):
            self.service.increment_counter(counter_name, tags={'iteration': str(i)})

        # Give background processing time
        import time
        time.sleep(1.5)

        # Retrieve counter metrics
        metrics = self.service.get_metrics(name=counter_name)

        self.assertEqual(len(metrics), 5)
        for metric in metrics:
            self.assertEqual(metric.type, MetricType.COUNTER)
            self.assertEqual(metric.value, 1.0)

    def test_histogram_recording(self):
        """Test histogram metric recording"""
        histogram_name = 'response_time'
        values = [100, 150, 200, 120, 180]

        for value in values:
            self.service.record_histogram(histogram_name, value, unit='ms')

        # Give background processing time
        import time
        time.sleep(1.5)

        metrics = self.service.get_metrics(name=histogram_name)

        self.assertEqual(len(metrics), len(values))
        recorded_values = [m.value for m in metrics]
        self.assertEqual(set(recorded_values), set(values))

    def test_performance_monitoring_decorator(self):
        """Test performance monitoring decorator"""
        @self.service.monitor_performance('test_operation', target_ms=100)
        def slow_operation():
            import time
            time.sleep(0.05)  # 50ms
            return "completed"

        @self.service.monitor_performance('test_operation_slow', target_ms=10)
        def very_slow_operation():
            import time
            time.sleep(0.05)  # 50ms - exceeds 10ms target
            return "completed"

        # Execute operations
        result1 = slow_operation()
        result2 = very_slow_operation()

        self.assertEqual(result1, "completed")
        self.assertEqual(result2, "completed")

        # Give background processing time
        import time
        time.sleep(1.5)

        # Check metrics were recorded
        duration_metrics = self.service.get_metrics(name='test_operation.duration')
        success_metrics = self.service.get_metrics(name='test_operation.success')

        self.assertGreater(len(duration_metrics), 0)
        self.assertGreater(len(success_metrics), 0)

        # Check alert was created for slow operation
        alerts = self.service.get_active_alerts()
        slow_alerts = [a for a in alerts if 'test_operation_slow' in a.name]
        self.assertGreater(len(slow_alerts), 0)

    def test_alert_creation_and_resolution(self):
        """Test alert creation and resolution"""
        alert_name = 'test_alert'
        alert_message = 'Test alert message'

        # Create alert
        self.service.create_alert(
            name=alert_name,
            severity=AlertSeverity.WARNING,
            message=alert_message,
            metric_name='test_metric',
            threshold_value=100,
            actual_value=150
        )

        # Give background processing time
        import time
        time.sleep(1.5)

        # Get active alerts
        active_alerts = self.service.get_active_alerts()
        test_alerts = [a for a in active_alerts if alert_name in a.name]

        self.assertGreater(len(test_alerts), 0)
        alert = test_alerts[0]
        self.assertEqual(alert.severity, AlertSeverity.WARNING)
        self.assertEqual(alert.message, alert_message)
        self.assertFalse(alert.resolved)

        # Resolve alert
        self.service.resolve_alert(alert.id)

        # Check alert is resolved
        active_alerts_after = self.service.get_active_alerts()
        test_alerts_after = [a for a in active_alerts_after if alert.id == a.id]
        self.assertEqual(len(test_alerts_after), 0)

    def test_health_checks(self):
        """Test health check system"""
        # Register custom health check
        def custom_health_check():
            from models.services.monitoring_service import HealthCheck, HealthStatus
            return HealthCheck(
                name='custom_check',
                status=HealthStatus.HEALTHY,
                message='Custom check passed',
                timestamp=datetime.now(),
                duration_ms=10
            )

        self.service.register_health_check('custom_check', custom_health_check)

        # Run specific health check
        result = self.service.run_health_check('custom_check')

        self.assertEqual(result.name, 'custom_check')
        self.assertEqual(result.status, HealthStatus.HEALTHY)
        self.assertEqual(result.message, 'Custom check passed')

        # Run all health checks
        all_results = self.service.run_all_health_checks()

        self.assertIn('custom_check', all_results)
        self.assertIn('database_connectivity', all_results)

        # Get system health
        system_health = self.service.get_system_health()

        self.assertIn('overall_status', system_health)
        self.assertIn('health_checks', system_health)
        self.assertIn('timestamp', system_health)

    def test_timer_context_manager(self):
        """Test timer context manager"""
        operation_name = 'timed_operation'

        with self.service.time_operation(operation_name, tags={'test': 'true'}):
            import time
            time.sleep(0.01)  # 10ms

        # Give background processing time
        import time
        time.sleep(1.5)

        # Check timing metric was recorded
        metrics = self.service.get_metrics(name=f'{operation_name}.duration')

        self.assertGreater(len(metrics), 0)
        metric = metrics[0]
        self.assertGreater(metric.value, 5)  # Should be > 5ms
        self.assertEqual(metric.unit, 'ms')

    def test_metric_export(self):
        """Test metric export functionality"""
        # Record some test metrics
        for i in range(3):
            self.service.record_metric(f'export_test_{i}', float(i), MetricType.GAUGE)

        # Give background processing time
        import time
        time.sleep(1.5)

        # Export as JSON
        json_export = self.service.export_metrics(format='json')
        self.assertIsInstance(json_export, str)

        # Parse JSON to verify structure
        data = json.loads(json_export)
        self.assertIsInstance(data, list)

        # Export as CSV
        csv_export = self.service.export_metrics(format='csv')
        self.assertIsInstance(csv_export, str)
        self.assertIn('name,type,value,timestamp', csv_export)


class TestIntegratedFeatures(unittest.TestCase):
    """Test integration between different medium priority features"""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name

        # Initialize all services
        self.progression_service = AdvancedProgressionService(self.db_path)
        self.security_service = SecurityService(self.db_path)
        self.monitoring_service = MonitoringService(self.db_path)

        self._init_test_data()

    def tearDown(self):
        self.monitoring_service.shutdown()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def _init_test_data(self):
        """Initialize test data for integration tests"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Create required tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT UNIQUE,
                    role TEXT DEFAULT 'user'
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS exercises (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL
                )
            """)

            cursor.execute("INSERT INTO users (id, username, role) VALUES (1, 'testuser', 'user')")
            cursor.execute("INSERT INTO exercises (id, name) VALUES (1, 'Bench Press')")

            conn.commit()

    def test_monitored_progression_analysis(self):
        """Test progression analysis with monitoring"""
        # Decorate progression method with monitoring
        @self.monitoring_service.monitor_performance('progression_analysis', target_ms=200)
        def analyze_progression():
            return self.progression_service.detect_advanced_pattern(user_id=1, exercise_id=1)

        # Execute monitored analysis
        result = analyze_progression()

        # Verify progression analysis result
        self.assertIsInstance(result, PatternAnalysis)

        # Give monitoring time to process
        import time
        time.sleep(1.5)

        # Verify monitoring metrics were recorded
        metrics = self.monitoring_service.get_metrics(name='progression_analysis.duration')
        self.assertGreater(len(metrics), 0)

        success_metrics = self.monitoring_service.get_metrics(name='progression_analysis.success')
        self.assertGreater(len(success_metrics), 0)

    @patch('models.services.security_service.SecurityService._get_current_user_id')
    def test_secure_progression_access(self, mock_get_user_id):
        """Test secure access to progression data"""
        mock_get_user_id.return_value = 1

        @self.security_service.require_user_access([AccessLevel.USER])
        @self.monitoring_service.monitor_performance('secure_progression_access')
        def get_secure_progression_data(current_user_id=None):
            # Log the data access
            self.security_service.log_audit_event(
                user_id=current_user_id,
                action=AuditAction.VIEW_DATA,
                resource_type='progression_data',
                resource_id=1
            )

            # Get progression data
            return self.progression_service.detect_advanced_pattern(
                user_id=current_user_id,
                exercise_id=1
            )

        # Execute secure access
        result = get_secure_progression_data()

        # Verify result
        self.assertIsInstance(result, PatternAnalysis)

        # Give time for background processing
        import time
        time.sleep(1.5)

        # Verify audit trail was created
        audit_entries = self.security_service.get_audit_trail(user_id=1, limit=10)
        view_data_entries = [e for e in audit_entries if e.action == AuditAction.VIEW_DATA]
        self.assertGreater(len(view_data_entries), 0)

        # Verify monitoring metrics
        metrics = self.monitoring_service.get_metrics(name='secure_progression_access.duration')
        self.assertGreater(len(metrics), 0)

    def test_comprehensive_system_health(self):
        """Test comprehensive system health including all services"""
        # Create some activity across all services

        # Progression service activity
        self.progression_service.detect_advanced_pattern(user_id=1, exercise_id=1)

        # Security service activity
        session_token = self.security_service.create_session(user_id=1)
        self.security_service.validate_session(session_token)

        # Monitoring service activity
        self.monitoring_service.increment_counter('system_activity')

        # Give time for processing
        import time
        time.sleep(1.5)

        # Get comprehensive health status
        system_health = self.monitoring_service.get_system_health()
        security_metrics = self.security_service.get_security_metrics()

        # Verify health data
        self.assertIn('overall_status', system_health)
        self.assertIn('health_checks', system_health)

        # Verify security metrics
        self.assertIn('active_sessions', security_metrics)
        self.assertGreater(security_metrics['active_sessions'], 0)

        # Verify monitoring metrics
        activity_metrics = self.monitoring_service.get_metrics(name='system_activity')
        self.assertGreater(len(activity_metrics), 0)


if __name__ == '__main__':
    # Configure logging for tests
    import logging
    logging.basicConfig(level=logging.WARNING)

    # Run all tests
    unittest.main(verbosity=2)
