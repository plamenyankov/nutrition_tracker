"""
Performance Monitoring and Observability for Progression System
Implements monitoring as per PROGRESSION_DASHBOARD_IMPROVEMENTS.md
"""

import time
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from functools import wraps
from dataclasses import dataclass
import json
import os

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    """Individual performance metric data"""
    operation_name: str
    duration_ms: float
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None
    user_id: Optional[int] = None

@dataclass
class HealthCheckResult:
    """Health check result data"""
    check_name: str
    status: str  # 'healthy', 'warning', 'critical'
    response_time_ms: float
    timestamp: datetime
    details: Optional[str] = None

class ProgressionMonitor:
    """Performance monitoring and observability system"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.getenv('DATABASE_PATH', 'database.db')
        self.metrics_buffer: List[PerformanceMetric] = []
        self.health_checks: Dict[str, HealthCheckResult] = {}

        # Performance targets
        self.targets = {
            'dashboard_load_ms': 2000,
            'chart_render_ms': 500,
            'pattern_detection_ms': 100,
            'error_rate_target': 0.001
        }

        # Initialize metrics storage
        self._init_metrics_storage()

    def _init_metrics_storage(self):
        """Initialize metrics storage table"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_name TEXT NOT NULL,
                    duration_ms REAL NOT NULL,
                    timestamp DATETIME NOT NULL,
                    success BOOLEAN NOT NULL,
                    error_message TEXT,
                    user_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_performance_metrics_operation
                ON performance_metrics(operation_name, timestamp)
            ''')

            conn.commit()
            conn.close()

        except sqlite3.Error as e:
            logger.error(f"Error initializing metrics storage: {e}")

    def monitor_performance(self, operation_name: str):
        """Decorator to monitor function performance"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                success = True
                error_message = None
                result = None

                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    error_message = str(e)
                    logger.error(f'{operation_name} failed: {e}')
                    raise
                finally:
                    duration_ms = (time.time() - start_time) * 1000

                    # Record metric
                    metric = PerformanceMetric(
                        operation_name=operation_name,
                        duration_ms=duration_ms,
                        timestamp=datetime.now(),
                        success=success,
                        error_message=error_message
                    )

                    self._record_metric(metric)
                    self._check_performance_target(operation_name, duration_ms)

            return wrapper
        return decorator

    def _record_metric(self, metric: PerformanceMetric):
        """Record a performance metric"""
        try:
            self.metrics_buffer.append(metric)

            # Flush buffer if it gets too large
            if len(self.metrics_buffer) >= 100:
                self._flush_metrics_buffer()

        except Exception as e:
            logger.error(f"Error recording metric: {e}")

    def _flush_metrics_buffer(self):
        """Flush metrics buffer to database"""
        if not self.metrics_buffer:
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            for metric in self.metrics_buffer:
                cursor.execute('''
                    INSERT INTO performance_metrics
                    (operation_name, duration_ms, timestamp, success, error_message, user_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    metric.operation_name,
                    metric.duration_ms,
                    metric.timestamp,
                    metric.success,
                    metric.error_message,
                    metric.user_id
                ))

            conn.commit()
            conn.close()

            logger.info(f"Flushed {len(self.metrics_buffer)} metrics to database")
            self.metrics_buffer.clear()

        except sqlite3.Error as e:
            logger.error(f"Error flushing metrics buffer: {e}")

    def _check_performance_target(self, operation_name: str, duration_ms: float):
        """Check if operation meets performance targets"""
        if operation_name == 'dashboard_load' and duration_ms > self.targets['dashboard_load_ms']:
            logger.warning(f"Dashboard load exceeded target: {duration_ms:.1f}ms > {self.targets['dashboard_load_ms']}ms")

        elif operation_name == 'chart_render' and duration_ms > self.targets['chart_render_ms']:
            logger.warning(f"Chart rendering exceeded target: {duration_ms:.1f}ms > {self.targets['chart_render_ms']}ms")

        elif operation_name == 'pattern_detection' and duration_ms > self.targets['pattern_detection_ms']:
            logger.warning(f"Pattern detection exceeded target: {duration_ms:.1f}ms > {self.targets['pattern_detection_ms']}ms")

# Global monitor instance
_monitor_instance = None

def get_monitor() -> ProgressionMonitor:
    """Get the global monitor instance (singleton pattern)"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = ProgressionMonitor()
    return _monitor_instance

# Convenience decorator for monitoring
def monitor_performance(operation_name: str):
    """Convenience decorator that uses the global monitor"""
    return get_monitor().monitor_performance(operation_name)
