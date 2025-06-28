"""
Configuration Management for Progression System
Centralizes all configurable values as per PROGRESSION_DASHBOARD_IMPROVEMENTS.md
"""

import os
import json
from typing import Dict, Any
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)

@dataclass
class PatternDetectionConfig:
    """Configuration for pattern detection algorithms"""
    min_workouts: int = 3
    analysis_window: int = 5
    confidence_threshold: float = 0.7
    cache_ttl_hours: int = 24

@dataclass
class VolumeTrackingConfig:
    """Configuration for volume tracking and calculations"""
    default_window_days: int = 30
    cache_ttl_hours: int = 24
    min_volume_for_trend: float = 100.0  # Minimum volume to calculate trends
    volume_change_threshold: float = 10.0  # % change to consider significant

@dataclass
class ProgressionThresholds:
    """Configuration for progression readiness thresholds"""
    ready_consecutive_workouts: int = 3
    close_rep_tolerance: int = 2
    building_percentage: float = 0.8
    max_weight_jump_percentage: float = 50.0  # Maximum allowed weight increase %
    min_rest_days: int = 1  # Minimum rest days between progressions

@dataclass
class DefaultUserPreferences:
    """Default user preferences for new users"""
    progression_strategy: str = 'reps_first'
    min_reps_target: int = 10
    max_reps_target: int = 15
    weight_increment_upper: float = 5.0  # kg - unified increment
    weight_increment_lower: float = 5.0  # kg - unified increment
    rest_timer_enabled: bool = True
    progression_notification_enabled: bool = True
    pyramid_preference: str = 'auto_detect'

@dataclass
class PerformanceTargets:
    """Performance benchmarks and targets"""
    initial_page_load_ms: int = 2000
    chart_rendering_ms: int = 500
    pattern_detection_ms: int = 100
    cache_hit_rate_target: float = 0.8
    error_rate_target: float = 0.001  # 0.1%

@dataclass
class DatabaseConfig:
    """Database optimization settings"""
    query_timeout_seconds: int = 30
    max_connections: int = 10
    enable_wal_mode: bool = True
    enable_foreign_keys: bool = True

class ProgressionConfig:
    """Main configuration class for the progression system"""

    def __init__(self, config_file: str = None):
        self.config_file = config_file or os.getenv('PROGRESSION_CONFIG_FILE', 'progression_config.json')

        # Initialize with defaults
        self.pattern_detection = PatternDetectionConfig()
        self.volume_tracking = VolumeTrackingConfig()
        self.progression_thresholds = ProgressionThresholds()
        self.default_user_preferences = DefaultUserPreferences()
        self.performance_targets = PerformanceTargets()
        self.database_config = DatabaseConfig()

        # Load from file if exists
        self.load_config()

    def load_config(self) -> bool:
        """Load configuration from JSON file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)

                # Update configurations from file
                if 'pattern_detection' in config_data:
                    self._update_dataclass(self.pattern_detection, config_data['pattern_detection'])

                if 'volume_tracking' in config_data:
                    self._update_dataclass(self.volume_tracking, config_data['volume_tracking'])

                if 'progression_thresholds' in config_data:
                    self._update_dataclass(self.progression_thresholds, config_data['progression_thresholds'])

                if 'default_user_preferences' in config_data:
                    self._update_dataclass(self.default_user_preferences, config_data['default_user_preferences'])

                if 'performance_targets' in config_data:
                    self._update_dataclass(self.performance_targets, config_data['performance_targets'])

                if 'database_config' in config_data:
                    self._update_dataclass(self.database_config, config_data['database_config'])

                logger.info(f"Configuration loaded from {self.config_file}")
                return True
            else:
                logger.info(f"Config file {self.config_file} not found, using defaults")
                return False

        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return False

    def save_config(self) -> bool:
        """Save current configuration to JSON file"""
        try:
            config_data = {
                'pattern_detection': asdict(self.pattern_detection),
                'volume_tracking': asdict(self.volume_tracking),
                'progression_thresholds': asdict(self.progression_thresholds),
                'default_user_preferences': asdict(self.default_user_preferences),
                'performance_targets': asdict(self.performance_targets),
                'database_config': asdict(self.database_config)
            }

            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)

            logger.info(f"Configuration saved to {self.config_file}")
            return True

        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            return False

    def _update_dataclass(self, dataclass_instance, update_dict: Dict[str, Any]):
        """Update dataclass instance with values from dictionary"""
        for key, value in update_dict.items():
            if hasattr(dataclass_instance, key):
                setattr(dataclass_instance, key, value)

    def get_user_preference_defaults(self) -> Dict[str, Any]:
        """Get default user preferences as dictionary"""
        return asdict(self.default_user_preferences)

    def validate_config(self) -> Dict[str, Any]:
        """Validate configuration values and return validation results"""
        issues = []
        warnings = []

        # Validate pattern detection
        if self.pattern_detection.min_workouts < 2:
            issues.append("min_workouts must be at least 2")

        if self.pattern_detection.confidence_threshold < 0.5 or self.pattern_detection.confidence_threshold > 1.0:
            warnings.append("confidence_threshold should be between 0.5 and 1.0")

        # Validate volume tracking
        if self.volume_tracking.default_window_days < 7:
            warnings.append("default_window_days less than 7 may not provide meaningful trends")

        # Validate progression thresholds
        if self.progression_thresholds.ready_consecutive_workouts < 2:
            issues.append("ready_consecutive_workouts must be at least 2")

        if self.progression_thresholds.max_weight_jump_percentage > 100:
            warnings.append("max_weight_jump_percentage over 100% may allow unrealistic progressions")

        # Validate user preferences
        if self.default_user_preferences.min_reps_target >= self.default_user_preferences.max_reps_target:
            issues.append("min_reps_target must be less than max_reps_target")

        if self.default_user_preferences.weight_increment_upper <= 0 or self.default_user_preferences.weight_increment_lower <= 0:
            issues.append("weight increments must be positive")

        # Validate performance targets
        if self.performance_targets.initial_page_load_ms > 5000:
            warnings.append("initial_page_load_ms target over 5 seconds may impact user experience")

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        }

    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration"""
        return {
            'pattern_detection': asdict(self.pattern_detection),
            'volume_tracking': asdict(self.volume_tracking),
            'progression_thresholds': asdict(self.progression_thresholds),
            'default_user_preferences': asdict(self.default_user_preferences),
            'performance_targets': asdict(self.performance_targets),
            'database_config': asdict(self.database_config),
            'validation': self.validate_config()
        }

# Global configuration instance
_config_instance = None

def get_config() -> ProgressionConfig:
    """Get the global configuration instance (singleton pattern)"""
    global _config_instance
    if _config_instance is None:
        _config_instance = ProgressionConfig()
    return _config_instance

def reload_config() -> bool:
    """Reload configuration from file"""
    global _config_instance
    if _config_instance is not None:
        return _config_instance.load_config()
    return False

# Environment-specific configurations
def get_development_config() -> ProgressionConfig:
    """Get configuration optimized for development"""
    config = ProgressionConfig()

    # More lenient thresholds for development
    config.pattern_detection.min_workouts = 2
    config.pattern_detection.confidence_threshold = 0.6
    config.progression_thresholds.ready_consecutive_workouts = 2

    # Faster cache expiry for development
    config.pattern_detection.cache_ttl_hours = 1
    config.volume_tracking.cache_ttl_hours = 1

    return config

def get_production_config() -> ProgressionConfig:
    """Get configuration optimized for production"""
    config = ProgressionConfig()

    # Stricter thresholds for production
    config.pattern_detection.confidence_threshold = 0.8
    config.progression_thresholds.ready_consecutive_workouts = 3

    # Longer cache for production
    config.pattern_detection.cache_ttl_hours = 24
    config.volume_tracking.cache_ttl_hours = 24

    # Stricter performance targets
    config.performance_targets.initial_page_load_ms = 1500
    config.performance_targets.chart_rendering_ms = 300

    return config
