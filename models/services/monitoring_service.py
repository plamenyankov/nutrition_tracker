"""
Advanced Monitoring & Observability Service for Progression Dashboard
Implements comprehensive monitoring, alerting, and health checks
"""

import logging
import sqlite3
import time
import json
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from functools import wraps
import threading
import queue
import os

class MetricType(Enum):
    """Types of metrics to track"""
    COUNTER = "counter"
    HISTOGRAM = "histogram"
    GAUGE = "gauge"
    TIMER = "timer"

class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class HealthStatus(Enum):
    """Health check status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

@dataclass
class Metric:
    """Metric data structure"""
    name: str
    type: MetricType
    value: float
    timestamp: datetime
    tags: Dict[str, str] = None
    unit: str = None

@dataclass
class Alert:
    """Alert data structure"""
    id: str
    name: str
    severity: AlertSeverity
    message: str
    timestamp: datetime
    metric_name: str
    threshold_value: float
    actual_value: float
    tags: Dict[str, str] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None

@dataclass
class HealthCheck:
    """Health check result"""
    name: str
    status: HealthStatus
    message: str
    timestamp: datetime
    duration_ms: float
    details: Dict[str, Any] = None

@dataclass
class PerformanceTarget:
    """Performance target configuration"""
    metric_name: str
    target_value: float
    operator: str  # 'lt', 'gt', 'eq', 'lte', 'gte'
    severity: AlertSeverity
    description: str

class MonitoringService:
    """Advanced monitoring and observability service"""

    def __init__(self, db_path: str = 'database.db'):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)

        # Metrics buffer for batch processing
        self.metrics_buffer = queue.Queue(maxsize=1000)
        self.alerts_buffer = queue.Queue(maxsize=100)

        # Performance targets from configuration
        self.performance_targets = self._load_performance_targets()

        # Health check registry
        self.health_checks = {}

        # Background processing
        self.processing_thread = None
        self.stop_processing = threading.Event()

        self._init_monitoring_tables()
        self._start_background_processing()
        self._register_default_health_checks()

    def _init_monitoring_tables(self):
        """Initialize monitoring database tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Metrics table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        type TEXT NOT NULL,
                        value REAL NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        tags TEXT,
                        unit TEXT
                    )
                """)

                # Alerts table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS alerts (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        message TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metric_name TEXT,
                        threshold_value REAL,
                        actual_value REAL,
                        tags TEXT,
                        resolved BOOLEAN DEFAULT 0,
                        resolved_at TIMESTAMP
                    )
                """)

                # Health checks table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS health_checks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        status TEXT NOT NULL,
                        message TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        duration_ms REAL,
                        details TEXT
                    )
                """)

                # Performance metrics aggregation table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS metric_aggregates (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        metric_name TEXT NOT NULL,
                        aggregation_type TEXT NOT NULL,
                        value REAL NOT NULL,
                        period_start TIMESTAMP NOT NULL,
                        period_end TIMESTAMP NOT NULL,
                        sample_count INTEGER DEFAULT 1
                    )
                """)

                # Create indexes for performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_name_timestamp ON metrics(name, timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_health_checks_timestamp ON health_checks(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_metric_aggregates_name_period ON metric_aggregates(metric_name, period_start)")

                conn.commit()
                self.logger.info("Monitoring tables initialized successfully")

        except Exception as e:
            self.logger.error(f"Error initializing monitoring tables: {e}")
            raise

    def _load_performance_targets(self) -> List[PerformanceTarget]:
        """Load performance targets from configuration"""
        return [
            PerformanceTarget(
                metric_name="dashboard_load_time",
                target_value=2000,  # 2 seconds in ms
                operator="lt",
                severity=AlertSeverity.WARNING,
                description="Dashboard should load in under 2 seconds"
            ),
            PerformanceTarget(
                metric_name="pattern_detection_time",
                target_value=100,  # 100ms
                operator="lt",
                severity=AlertSeverity.WARNING,
                description="Pattern detection should complete in under 100ms"
            ),
            PerformanceTarget(
                metric_name="query_execution_time",
                target_value=500,  # 500ms
                operator="lt",
                severity=AlertSeverity.ERROR,
                description="Database queries should complete in under 500ms"
            ),
            PerformanceTarget(
                metric_name="error_rate",
                target_value=0.1,  # 0.1%
                operator="lt",
                severity=AlertSeverity.CRITICAL,
                description="Error rate should be below 0.1%"
            ),
            PerformanceTarget(
                metric_name="cache_hit_rate",
                target_value=80,  # 80%
                operator="gt",
                severity=AlertSeverity.WARNING,
                description="Cache hit rate should be above 80%"
            )
        ]

    def monitor_performance(self, operation_name: str, target_ms: float = None):
        """Decorator to monitor function performance"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                error_occurred = False

                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    error_occurred = True
                    self.increment_counter(f"{operation_name}.error", tags={'error_type': type(e).__name__})
                    raise
                finally:
                    duration_ms = (time.time() - start_time) * 1000

                    # Record timing metric
                    self.record_histogram(f"{operation_name}.duration", duration_ms, unit="ms")

                    # Record success/failure
                    if not error_occurred:
                        self.increment_counter(f"{operation_name}.success")

                    # Check against target if specified
                    if target_ms and duration_ms > target_ms:
                        self.create_alert(
                            name=f"{operation_name}_slow",
                            severity=AlertSeverity.WARNING,
                            message=f"{operation_name} took {duration_ms:.2f}ms (target: {target_ms}ms)",
                            metric_name=f"{operation_name}.duration",
                            threshold_value=target_ms,
                            actual_value=duration_ms
                        )

            return wrapper
        return decorator

    def record_metric(self, name: str, value: float, metric_type: MetricType = MetricType.GAUGE,
                     tags: Dict[str, str] = None, unit: str = None):
        """Record a metric"""
        metric = Metric(
            name=name,
            type=metric_type,
            value=value,
            timestamp=datetime.now(),
            tags=tags,
            unit=unit
        )

        try:
            self.metrics_buffer.put_nowait(metric)
        except queue.Full:
            self.logger.warning("Metrics buffer full, dropping metric")

        # Check against performance targets
        self._check_performance_targets(metric)

    def increment_counter(self, name: str, value: float = 1.0, tags: Dict[str, str] = None):
        """Increment a counter metric"""
        self.record_metric(name, value, MetricType.COUNTER, tags)

    def record_histogram(self, name: str, value: float, tags: Dict[str, str] = None, unit: str = None):
        """Record a histogram metric"""
        self.record_metric(name, value, MetricType.HISTOGRAM, tags, unit)

    def set_gauge(self, name: str, value: float, tags: Dict[str, str] = None, unit: str = None):
        """Set a gauge metric"""
        self.record_metric(name, value, MetricType.GAUGE, tags, unit)

    def time_operation(self, name: str, tags: Dict[str, str] = None):
        """Context manager to time operations"""
        return TimerContext(self, name, tags)

    def create_alert(self, name: str, severity: AlertSeverity, message: str,
                    metric_name: str = None, threshold_value: float = None,
                    actual_value: float = None, tags: Dict[str, str] = None):
        """Create an alert"""
        alert_id = f"{name}_{int(time.time())}"
        alert = Alert(
            id=alert_id,
            name=name,
            severity=severity,
            message=message,
            timestamp=datetime.now(),
            metric_name=metric_name,
            threshold_value=threshold_value,
            actual_value=actual_value,
            tags=tags
        )

        try:
            self.alerts_buffer.put_nowait(alert)
            self.logger.log(
                self._severity_to_log_level(severity),
                f"Alert created: {name} - {message}"
            )
        except queue.Full:
            self.logger.error("Alerts buffer full, dropping alert")

    def register_health_check(self, name: str, check_func: Callable[[], HealthCheck]):
        """Register a health check function"""
        self.health_checks[name] = check_func

    def run_health_check(self, name: str) -> HealthCheck:
        """Run a specific health check"""
        if name not in self.health_checks:
            return HealthCheck(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check '{name}' not found",
                timestamp=datetime.now(),
                duration_ms=0
            )

        start_time = time.time()
        try:
            result = self.health_checks[name]()
            result.duration_ms = (time.time() - start_time) * 1000
            return result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                timestamp=datetime.now(),
                duration_ms=duration_ms
            )

    def run_all_health_checks(self) -> Dict[str, HealthCheck]:
        """Run all registered health checks"""
        results = {}
        for name in self.health_checks:
            results[name] = self.run_health_check(name)
        return results

    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        health_results = self.run_all_health_checks()

        # Determine overall status
        statuses = [check.status for check in health_results.values()]
        if any(status == HealthStatus.UNHEALTHY for status in statuses):
            overall_status = HealthStatus.UNHEALTHY
        elif any(status == HealthStatus.DEGRADED for status in statuses):
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY

        # Get recent metrics
        recent_metrics = self.get_recent_metrics(minutes=5)

        # Get active alerts
        active_alerts = self.get_active_alerts()

        return {
            'overall_status': overall_status.value,
            'timestamp': datetime.now().isoformat(),
            'health_checks': {name: asdict(check) for name, check in health_results.items()},
            'recent_metrics_count': len(recent_metrics),
            'active_alerts_count': len(active_alerts),
            'performance_summary': self._get_performance_summary()
        }

    def get_metrics(self, name: str = None, start_time: datetime = None,
                   end_time: datetime = None, limit: int = 1000) -> List[Metric]:
        """Retrieve metrics from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                query = "SELECT * FROM metrics WHERE 1=1"
                params = []

                if name:
                    query += " AND name = ?"
                    params.append(name)

                if start_time:
                    query += " AND timestamp >= ?"
                    params.append(start_time)

                if end_time:
                    query += " AND timestamp <= ?"
                    params.append(end_time)

                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)

                cursor.execute(query, params)
                rows = cursor.fetchall()

                metrics = []
                for row in rows:
                    tags = json.loads(row[5]) if row[5] else None
                    metrics.append(Metric(
                        name=row[1],
                        type=MetricType(row[2]),
                        value=row[3],
                        timestamp=datetime.fromisoformat(row[4]),
                        tags=tags,
                        unit=row[6]
                    ))

                return metrics

        except Exception as e:
            self.logger.error(f"Error retrieving metrics: {e}")
            return []

    def get_recent_metrics(self, minutes: int = 60) -> List[Metric]:
        """Get metrics from the last N minutes"""
        start_time = datetime.now() - timedelta(minutes=minutes)
        return self.get_metrics(start_time=start_time)

    def get_active_alerts(self) -> List[Alert]:
        """Get all active (unresolved) alerts"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM alerts
                    WHERE resolved = 0
                    ORDER BY timestamp DESC
                """)

                rows = cursor.fetchall()
                alerts = []

                for row in rows:
                    tags = json.loads(row[8]) if row[8] else None
                    alerts.append(Alert(
                        id=row[0],
                        name=row[1],
                        severity=AlertSeverity(row[2]),
                        message=row[3],
                        timestamp=datetime.fromisoformat(row[4]),
                        metric_name=row[5],
                        threshold_value=row[6],
                        actual_value=row[7],
                        tags=tags,
                        resolved=bool(row[9]),
                        resolved_at=datetime.fromisoformat(row[10]) if row[10] else None
                    ))

                return alerts

        except Exception as e:
            self.logger.error(f"Error retrieving active alerts: {e}")
            return []

    def resolve_alert(self, alert_id: str):
        """Resolve an alert"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE alerts
                    SET resolved = 1, resolved_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (alert_id,))

                conn.commit()
                self.logger.info(f"Alert {alert_id} resolved")

        except Exception as e:
            self.logger.error(f"Error resolving alert: {e}")

    def get_metric_aggregates(self, metric_name: str, aggregation_type: str = 'avg',
                             period_hours: int = 24) -> List[Dict[str, Any]]:
        """Get aggregated metrics for a time period"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                start_time = datetime.now() - timedelta(hours=period_hours)

                cursor.execute("""
                    SELECT period_start, period_end, value, sample_count
                    FROM metric_aggregates
                    WHERE metric_name = ? AND aggregation_type = ?
                    AND period_start >= ?
                    ORDER BY period_start
                """, (metric_name, aggregation_type, start_time))

                rows = cursor.fetchall()

                return [{
                    'period_start': row[0],
                    'period_end': row[1],
                    'value': row[2],
                    'sample_count': row[3]
                } for row in rows]

        except Exception as e:
            self.logger.error(f"Error retrieving metric aggregates: {e}")
            return []

    def export_metrics(self, format: str = 'json', start_time: datetime = None,
                      end_time: datetime = None) -> str:
        """Export metrics in specified format"""
        metrics = self.get_metrics(start_time=start_time, end_time=end_time)

        if format.lower() == 'json':
            return json.dumps([asdict(metric) for metric in metrics], default=str, indent=2)
        elif format.lower() == 'csv':
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow(['name', 'type', 'value', 'timestamp', 'tags', 'unit'])

            # Write data
            for metric in metrics:
                writer.writerow([
                    metric.name,
                    metric.type.value,
                    metric.value,
                    metric.timestamp.isoformat(),
                    json.dumps(metric.tags) if metric.tags else '',
                    metric.unit or ''
                ])

            return output.getvalue()
        else:
            raise ValueError(f"Unsupported export format: {format}")

    # Private methods

    def _start_background_processing(self):
        """Start background thread for processing metrics and alerts"""
        self.processing_thread = threading.Thread(target=self._process_buffers, daemon=True)
        self.processing_thread.start()

    def _process_buffers(self):
        """Background processing of metrics and alerts buffers"""
        while not self.stop_processing.is_set():
            try:
                # Process metrics
                metrics_to_process = []
                while not self.metrics_buffer.empty() and len(metrics_to_process) < 100:
                    try:
                        metric = self.metrics_buffer.get_nowait()
                        metrics_to_process.append(metric)
                    except queue.Empty:
                        break

                if metrics_to_process:
                    self._store_metrics(metrics_to_process)

                # Process alerts
                alerts_to_process = []
                while not self.alerts_buffer.empty() and len(alerts_to_process) < 50:
                    try:
                        alert = self.alerts_buffer.get_nowait()
                        alerts_to_process.append(alert)
                    except queue.Empty:
                        break

                if alerts_to_process:
                    self._store_alerts(alerts_to_process)

                # Sleep briefly
                time.sleep(1)

            except Exception as e:
                self.logger.error(f"Error in background processing: {e}")
                time.sleep(5)

    def _store_metrics(self, metrics: List[Metric]):
        """Store metrics in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                for metric in metrics:
                    cursor.execute("""
                        INSERT INTO metrics (name, type, value, timestamp, tags, unit)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        metric.name,
                        metric.type.value,
                        metric.value,
                        metric.timestamp,
                        json.dumps(metric.tags) if metric.tags else None,
                        metric.unit
                    ))

                conn.commit()

        except Exception as e:
            self.logger.error(f"Error storing metrics: {e}")

    def _store_alerts(self, alerts: List[Alert]):
        """Store alerts in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                for alert in alerts:
                    cursor.execute("""
                        INSERT OR REPLACE INTO alerts
                        (id, name, severity, message, timestamp, metric_name, threshold_value, actual_value, tags)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        alert.id,
                        alert.name,
                        alert.severity.value,
                        alert.message,
                        alert.timestamp,
                        alert.metric_name,
                        alert.threshold_value,
                        alert.actual_value,
                        json.dumps(alert.tags) if alert.tags else None
                    ))

                conn.commit()

        except Exception as e:
            self.logger.error(f"Error storing alerts: {e}")

    def _check_performance_targets(self, metric: Metric):
        """Check metric against performance targets"""
        for target in self.performance_targets:
            if target.metric_name == metric.name:
                violation = False

                if target.operator == 'lt' and metric.value >= target.target_value:
                    violation = True
                elif target.operator == 'gt' and metric.value <= target.target_value:
                    violation = True
                elif target.operator == 'eq' and metric.value != target.target_value:
                    violation = True
                elif target.operator == 'lte' and metric.value > target.target_value:
                    violation = True
                elif target.operator == 'gte' and metric.value < target.target_value:
                    violation = True

                if violation:
                    self.create_alert(
                        name=f"{target.metric_name}_target_violation",
                        severity=target.severity,
                        message=f"{target.description}. Current: {metric.value}, Target: {target.operator} {target.target_value}",
                        metric_name=metric.name,
                        threshold_value=target.target_value,
                        actual_value=metric.value
                    )

    def _register_default_health_checks(self):
        """Register default health checks"""
        self.register_health_check('database_connectivity', self._check_database_connectivity)
        self.register_health_check('disk_space', self._check_disk_space)
        self.register_health_check('memory_usage', self._check_memory_usage)
        self.register_health_check('recent_errors', self._check_recent_errors)

    def _check_database_connectivity(self) -> HealthCheck:
        """Check database connectivity"""
        try:
            with sqlite3.connect(self.db_path, timeout=5) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()

            return HealthCheck(
                name='database_connectivity',
                status=HealthStatus.HEALTHY,
                message='Database connection successful',
                timestamp=datetime.now(),
                duration_ms=0
            )
        except Exception as e:
            return HealthCheck(
                name='database_connectivity',
                status=HealthStatus.UNHEALTHY,
                message=f'Database connection failed: {str(e)}',
                timestamp=datetime.now(),
                duration_ms=0
            )

    def _check_disk_space(self) -> HealthCheck:
        """Check available disk space"""
        try:
            import shutil
            total, used, free = shutil.disk_usage(os.path.dirname(self.db_path))
            free_percent = (free / total) * 100

            if free_percent < 5:
                status = HealthStatus.UNHEALTHY
                message = f'Critical: Only {free_percent:.1f}% disk space remaining'
            elif free_percent < 15:
                status = HealthStatus.DEGRADED
                message = f'Warning: Only {free_percent:.1f}% disk space remaining'
            else:
                status = HealthStatus.HEALTHY
                message = f'Disk space OK: {free_percent:.1f}% available'

            return HealthCheck(
                name='disk_space',
                status=status,
                message=message,
                timestamp=datetime.now(),
                duration_ms=0,
                details={'free_percent': free_percent, 'free_bytes': free}
            )
        except Exception as e:
            return HealthCheck(
                name='disk_space',
                status=HealthStatus.UNHEALTHY,
                message=f'Disk space check failed: {str(e)}',
                timestamp=datetime.now(),
                duration_ms=0
            )

    def _check_memory_usage(self) -> HealthCheck:
        """Check memory usage"""
        try:
            import psutil
            memory = psutil.virtual_memory()

            if memory.percent > 90:
                status = HealthStatus.UNHEALTHY
                message = f'Critical: Memory usage at {memory.percent:.1f}%'
            elif memory.percent > 80:
                status = HealthStatus.DEGRADED
                message = f'Warning: Memory usage at {memory.percent:.1f}%'
            else:
                status = HealthStatus.HEALTHY
                message = f'Memory usage OK: {memory.percent:.1f}%'

            return HealthCheck(
                name='memory_usage',
                status=status,
                message=message,
                timestamp=datetime.now(),
                duration_ms=0,
                details={'percent': memory.percent, 'available': memory.available}
            )
        except ImportError:
            return HealthCheck(
                name='memory_usage',
                status=HealthStatus.DEGRADED,
                message='psutil not available for memory monitoring',
                timestamp=datetime.now(),
                duration_ms=0
            )
        except Exception as e:
            return HealthCheck(
                name='memory_usage',
                status=HealthStatus.UNHEALTHY,
                message=f'Memory check failed: {str(e)}',
                timestamp=datetime.now(),
                duration_ms=0
            )

    def _check_recent_errors(self) -> HealthCheck:
        """Check for recent errors in logs"""
        try:
            # Check for recent error-level alerts
            recent_errors = [alert for alert in self.get_active_alerts()
                           if alert.severity in [AlertSeverity.ERROR, AlertSeverity.CRITICAL]]

            if len(recent_errors) > 5:
                status = HealthStatus.UNHEALTHY
                message = f'Critical: {len(recent_errors)} active error alerts'
            elif len(recent_errors) > 0:
                status = HealthStatus.DEGRADED
                message = f'Warning: {len(recent_errors)} active error alerts'
            else:
                status = HealthStatus.HEALTHY
                message = 'No recent errors detected'

            return HealthCheck(
                name='recent_errors',
                status=status,
                message=message,
                timestamp=datetime.now(),
                duration_ms=0,
                details={'error_count': len(recent_errors)}
            )
        except Exception as e:
            return HealthCheck(
                name='recent_errors',
                status=HealthStatus.UNHEALTHY,
                message=f'Error check failed: {str(e)}',
                timestamp=datetime.now(),
                duration_ms=0
            )

    def _get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for the last hour"""
        try:
            recent_metrics = self.get_recent_metrics(minutes=60)

            # Group metrics by name
            metric_groups = {}
            for metric in recent_metrics:
                if metric.name not in metric_groups:
                    metric_groups[metric.name] = []
                metric_groups[metric.name].append(metric.value)

            # Calculate summary statistics
            summary = {}
            for name, values in metric_groups.items():
                if values:
                    summary[name] = {
                        'count': len(values),
                        'avg': statistics.mean(values),
                        'min': min(values),
                        'max': max(values),
                        'p95': statistics.quantiles(values, n=20)[18] if len(values) >= 20 else max(values)
                    }

            return summary

        except Exception as e:
            self.logger.error(f"Error generating performance summary: {e}")
            return {}

    def _severity_to_log_level(self, severity: AlertSeverity) -> int:
        """Convert alert severity to logging level"""
        mapping = {
            AlertSeverity.INFO: logging.INFO,
            AlertSeverity.WARNING: logging.WARNING,
            AlertSeverity.ERROR: logging.ERROR,
            AlertSeverity.CRITICAL: logging.CRITICAL
        }
        return mapping.get(severity, logging.INFO)

    def cleanup_old_data(self, days: int = 30):
        """Clean up old monitoring data"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Clean up old metrics
                cursor.execute("DELETE FROM metrics WHERE timestamp < ?", (cutoff_date,))

                # Clean up resolved alerts older than cutoff
                cursor.execute("""
                    DELETE FROM alerts
                    WHERE resolved = 1 AND resolved_at < ?
                """, (cutoff_date,))

                # Clean up old health checks
                cursor.execute("DELETE FROM health_checks WHERE timestamp < ?", (cutoff_date,))

                # Clean up old metric aggregates
                cursor.execute("DELETE FROM metric_aggregates WHERE period_end < ?", (cutoff_date,))

                conn.commit()
                self.logger.info(f"Cleaned up monitoring data older than {days} days")

        except Exception as e:
            self.logger.error(f"Error cleaning up monitoring data: {e}")

    def shutdown(self):
        """Shutdown monitoring service"""
        self.stop_processing.set()
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
        self.logger.info("Monitoring service shutdown complete")


class TimerContext:
    """Context manager for timing operations"""

    def __init__(self, monitoring_service: MonitoringService, name: str, tags: Dict[str, str] = None):
        self.monitoring_service = monitoring_service
        self.name = name
        self.tags = tags
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration_ms = (time.time() - self.start_time) * 1000
            self.monitoring_service.record_histogram(
                f"{self.name}.duration",
                duration_ms,
                tags=self.tags,
                unit="ms"
            )


# Global monitoring service instance
monitoring_service = MonitoringService()


# Convenience decorators
def monitor_performance(operation_name: str, target_ms: float = None):
    """Decorator to monitor function performance"""
    return monitoring_service.monitor_performance(operation_name, target_ms)

def time_operation(name: str, tags: Dict[str, str] = None):
    """Context manager to time operations"""
    return monitoring_service.time_operation(name, tags)
