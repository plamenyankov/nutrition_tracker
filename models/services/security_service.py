"""
Security Service for Progression Dashboard
Implements enhanced data access control, audit trails, and security measures
"""

import logging
import sqlite3
import hashlib
import secrets
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from functools import wraps
import os

class AccessLevel(Enum):
    """User access levels"""
    USER = "user"
    COACH = "coach"
    ADMIN = "admin"

class AuditAction(Enum):
    """Audit trail actions"""
    LOGIN = "login"
    LOGOUT = "logout"
    VIEW_DATA = "view_data"
    MODIFY_DATA = "modify_data"
    PROGRESSION_ACCEPT = "progression_accept"
    PROGRESSION_REJECT = "progression_reject"
    EXPORT_DATA = "export_data"
    DELETE_DATA = "delete_data"
    PERMISSION_CHANGE = "permission_change"

@dataclass
class AuditEntry:
    """Audit trail entry"""
    user_id: int
    action: AuditAction
    resource_type: str
    resource_id: Optional[int]
    details: Dict[str, Any]
    timestamp: datetime
    ip_address: Optional[str]
    user_agent: Optional[str]

@dataclass
class SecurityPolicy:
    """Security policy configuration"""
    session_timeout_minutes: int = 480  # 8 hours
    max_failed_logins: int = 5
    lockout_duration_minutes: int = 30
    password_min_length: int = 8
    require_password_complexity: bool = True
    data_retention_days: int = 730  # 2 years
    audit_retention_days: int = 2555  # 7 years
    enable_data_encryption: bool = True

class SecurityService:
    """Enhanced security service for progression dashboard"""

    def __init__(self, db_path: str = 'database.db'):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self.policy = SecurityPolicy()
        self._init_security_tables()

    def _init_security_tables(self):
        """Initialize security-related database tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # User sessions table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        session_token TEXT UNIQUE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP NOT NULL,
                        ip_address TEXT,
                        user_agent TEXT,
                        is_active BOOLEAN DEFAULT 1,
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    )
                """)

                # Failed login attempts table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS failed_login_attempts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT,
                        ip_address TEXT,
                        attempt_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        user_agent TEXT
                    )
                """)

                # User permissions table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_permissions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        permission_type TEXT NOT NULL,
                        resource_type TEXT,
                        resource_id INTEGER,
                        granted_by INTEGER,
                        granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1,
                        FOREIGN KEY (user_id) REFERENCES users(id),
                        FOREIGN KEY (granted_by) REFERENCES users(id)
                    )
                """)

                # Audit trail table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS audit_trail (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        action TEXT NOT NULL,
                        resource_type TEXT,
                        resource_id INTEGER,
                        details TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        ip_address TEXT,
                        user_agent TEXT,
                        session_id TEXT
                    )
                """)

                # Data access log table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS data_access_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        accessed_user_id INTEGER,
                        resource_type TEXT NOT NULL,
                        resource_id INTEGER,
                        access_type TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        ip_address TEXT,
                        FOREIGN KEY (user_id) REFERENCES users(id),
                        FOREIGN KEY (accessed_user_id) REFERENCES users(id)
                    )
                """)

                # Create indexes for performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(session_token)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_user ON user_sessions(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_failed_logins_ip ON failed_login_attempts(ip_address)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_trail_user ON audit_trail(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_trail_timestamp ON audit_trail(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_data_access_user ON data_access_log(user_id)")

                conn.commit()
                self.logger.info("Security tables initialized successfully")

        except Exception as e:
            self.logger.error(f"Error initializing security tables: {e}")
            raise

    def require_user_access(self, allowed_access_levels: List[AccessLevel] = None):
        """Decorator to enforce user access control"""
        if allowed_access_levels is None:
            allowed_access_levels = [AccessLevel.USER, AccessLevel.COACH, AccessLevel.ADMIN]

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Get current user from session/context
                user_id = self._get_current_user_id()
                if not user_id:
                    raise SecurityError("Authentication required")

                # Check user access level
                user_access_level = self._get_user_access_level(user_id)
                if user_access_level not in allowed_access_levels:
                    raise SecurityError("Insufficient permissions")

                # Inject user_id into kwargs for automatic filtering
                kwargs['current_user_id'] = user_id

                # Log data access
                self._log_data_access(
                    user_id=user_id,
                    resource_type=func.__name__,
                    access_type='read'
                )

                return func(*args, **kwargs)
            return wrapper
        return decorator

    def require_data_ownership(self, data_user_id_param: str = 'user_id'):
        """Decorator to ensure users can only access their own data"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                current_user_id = kwargs.get('current_user_id')
                target_user_id = kwargs.get(data_user_id_param)

                if not current_user_id:
                    raise SecurityError("Authentication required")

                # Allow access if user is accessing their own data
                if current_user_id == target_user_id:
                    return func(*args, **kwargs)

                # Check if user has permission to access other user's data
                if self._has_permission(current_user_id, 'view_user_data', target_user_id):
                    self._log_data_access(
                        user_id=current_user_id,
                        accessed_user_id=target_user_id,
                        resource_type=func.__name__,
                        access_type='read'
                    )
                    return func(*args, **kwargs)

                raise SecurityError("Access denied: insufficient permissions")
            return wrapper
        return decorator

    def create_session(self, user_id: int, ip_address: str = None, user_agent: str = None) -> str:
        """Create a new user session"""
        try:
            session_token = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(minutes=self.policy.session_timeout_minutes)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO user_sessions (user_id, session_token, expires_at, ip_address, user_agent)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, session_token, expires_at, ip_address, user_agent))

                conn.commit()

            # Log session creation
            self.log_audit_event(
                user_id=user_id,
                action=AuditAction.LOGIN,
                details={'session_created': True},
                ip_address=ip_address,
                user_agent=user_agent
            )

            return session_token

        except Exception as e:
            self.logger.error(f"Error creating session: {e}")
            raise SecurityError("Failed to create session")

    def validate_session(self, session_token: str) -> Optional[int]:
        """Validate session and return user_id if valid"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT user_id, expires_at
                    FROM user_sessions
                    WHERE session_token = ? AND is_active = 1
                """, (session_token,))

                result = cursor.fetchone()

                if not result:
                    return None

                user_id, expires_at = result
                expires_datetime = datetime.fromisoformat(expires_at)

                if datetime.now() > expires_datetime:
                    # Session expired, deactivate it
                    cursor.execute("""
                        UPDATE user_sessions
                        SET is_active = 0
                        WHERE session_token = ?
                    """, (session_token,))
                    conn.commit()
                    return None

                return user_id

        except Exception as e:
            self.logger.error(f"Error validating session: {e}")
            return None

    def invalidate_session(self, session_token: str):
        """Invalidate a user session"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Get user_id before invalidating
                cursor.execute("SELECT user_id FROM user_sessions WHERE session_token = ?", (session_token,))
                result = cursor.fetchone()

                if result:
                    user_id = result[0]

                    # Invalidate session
                    cursor.execute("""
                        UPDATE user_sessions
                        SET is_active = 0
                        WHERE session_token = ?
                    """, (session_token,))

                    conn.commit()

                    # Log logout
                    self.log_audit_event(
                        user_id=user_id,
                        action=AuditAction.LOGOUT,
                        details={'session_invalidated': True}
                    )

        except Exception as e:
            self.logger.error(f"Error invalidating session: {e}")

    def record_failed_login(self, username: str, ip_address: str = None, user_agent: str = None):
        """Record a failed login attempt"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO failed_login_attempts (username, ip_address, user_agent)
                    VALUES (?, ?, ?)
                """, (username, ip_address, user_agent))

                conn.commit()

        except Exception as e:
            self.logger.error(f"Error recording failed login: {e}")

    def is_account_locked(self, username: str, ip_address: str = None) -> bool:
        """Check if account is locked due to failed login attempts"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Check failed attempts in the last lockout period
                lockout_start = datetime.now() - timedelta(minutes=self.policy.lockout_duration_minutes)

                cursor.execute("""
                    SELECT COUNT(*)
                    FROM failed_login_attempts
                    WHERE username = ? AND attempt_time > ?
                """, (username, lockout_start))

                failed_count = cursor.fetchone()[0]

                return failed_count >= self.policy.max_failed_logins

        except Exception as e:
            self.logger.error(f"Error checking account lock status: {e}")
            return False

    def grant_permission(self, user_id: int, permission_type: str, resource_type: str = None,
                        resource_id: int = None, granted_by: int = None, expires_at: datetime = None):
        """Grant permission to a user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO user_permissions
                    (user_id, permission_type, resource_type, resource_id, granted_by, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, permission_type, resource_type, resource_id, granted_by, expires_at))

                conn.commit()

                # Log permission grant
                self.log_audit_event(
                    user_id=granted_by or user_id,
                    action=AuditAction.PERMISSION_CHANGE,
                    resource_type='user_permission',
                    resource_id=user_id,
                    details={
                        'action': 'grant',
                        'permission_type': permission_type,
                        'resource_type': resource_type,
                        'resource_id': resource_id
                    }
                )

        except Exception as e:
            self.logger.error(f"Error granting permission: {e}")
            raise SecurityError("Failed to grant permission")

    def revoke_permission(self, user_id: int, permission_type: str, resource_type: str = None,
                         resource_id: int = None, revoked_by: int = None):
        """Revoke permission from a user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE user_permissions
                    SET is_active = 0
                    WHERE user_id = ? AND permission_type = ?
                    AND (resource_type = ? OR resource_type IS NULL)
                    AND (resource_id = ? OR resource_id IS NULL)
                    AND is_active = 1
                """, (user_id, permission_type, resource_type, resource_id))

                conn.commit()

                # Log permission revocation
                self.log_audit_event(
                    user_id=revoked_by or user_id,
                    action=AuditAction.PERMISSION_CHANGE,
                    resource_type='user_permission',
                    resource_id=user_id,
                    details={
                        'action': 'revoke',
                        'permission_type': permission_type,
                        'resource_type': resource_type,
                        'resource_id': resource_id
                    }
                )

        except Exception as e:
            self.logger.error(f"Error revoking permission: {e}")
            raise SecurityError("Failed to revoke permission")

    def log_audit_event(self, user_id: int, action: AuditAction, resource_type: str = None,
                       resource_id: int = None, details: Dict[str, Any] = None,
                       ip_address: str = None, user_agent: str = None, session_id: str = None):
        """Log an audit event"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO audit_trail
                    (user_id, action, resource_type, resource_id, details, ip_address, user_agent, session_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (user_id, action.value, resource_type, resource_id,
                     json.dumps(details) if details else None, ip_address, user_agent, session_id))

                conn.commit()

        except Exception as e:
            self.logger.error(f"Error logging audit event: {e}")

    def get_audit_trail(self, user_id: int = None, action: AuditAction = None,
                       start_date: datetime = None, end_date: datetime = None,
                       limit: int = 100) -> List[AuditEntry]:
        """Retrieve audit trail entries"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                query = "SELECT * FROM audit_trail WHERE 1=1"
                params = []

                if user_id:
                    query += " AND user_id = ?"
                    params.append(user_id)

                if action:
                    query += " AND action = ?"
                    params.append(action.value)

                if start_date:
                    query += " AND timestamp >= ?"
                    params.append(start_date)

                if end_date:
                    query += " AND timestamp <= ?"
                    params.append(end_date)

                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)

                cursor.execute(query, params)
                rows = cursor.fetchall()

                audit_entries = []
                for row in rows:
                    details = json.loads(row[5]) if row[5] else {}
                    audit_entries.append(AuditEntry(
                        user_id=row[1],
                        action=AuditAction(row[2]),
                        resource_type=row[3],
                        resource_id=row[4],
                        details=details,
                        timestamp=datetime.fromisoformat(row[6]),
                        ip_address=row[7],
                        user_agent=row[8]
                    ))

                return audit_entries

        except Exception as e:
            self.logger.error(f"Error retrieving audit trail: {e}")
            return []

    def cleanup_old_data(self):
        """Clean up old data according to retention policies"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Clean up old sessions
                session_cutoff = datetime.now() - timedelta(days=30)
                cursor.execute("""
                    DELETE FROM user_sessions
                    WHERE created_at < ? AND is_active = 0
                """, (session_cutoff,))

                # Clean up old failed login attempts
                login_cutoff = datetime.now() - timedelta(days=90)
                cursor.execute("""
                    DELETE FROM failed_login_attempts
                    WHERE attempt_time < ?
                """, (login_cutoff,))

                # Clean up old data access logs
                access_cutoff = datetime.now() - timedelta(days=self.policy.data_retention_days)
                cursor.execute("""
                    DELETE FROM data_access_log
                    WHERE timestamp < ?
                """, (access_cutoff,))

                # Clean up old audit trail (keep longer for compliance)
                audit_cutoff = datetime.now() - timedelta(days=self.policy.audit_retention_days)
                cursor.execute("""
                    DELETE FROM audit_trail
                    WHERE timestamp < ?
                """, (audit_cutoff,))

                conn.commit()
                self.logger.info("Old data cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during data cleanup: {e}")

    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data (placeholder - implement with proper encryption)"""
        if not self.policy.enable_data_encryption:
            return data

        # This is a placeholder - implement proper encryption with a key management system
        # For production, use libraries like cryptography.fernet or similar
        return hashlib.sha256(data.encode()).hexdigest()

    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data (placeholder - implement with proper decryption)"""
        if not self.policy.enable_data_encryption:
            return encrypted_data

        # This is a placeholder - implement proper decryption
        # For production, use proper decryption with the same key management system
        return encrypted_data  # Cannot reverse hash - this is just a placeholder

    def get_security_metrics(self) -> Dict[str, Any]:
        """Get security metrics for monitoring"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Active sessions count
                cursor.execute("SELECT COUNT(*) FROM user_sessions WHERE is_active = 1")
                active_sessions = cursor.fetchone()[0]

                # Failed login attempts in last 24 hours
                yesterday = datetime.now() - timedelta(days=1)
                cursor.execute("""
                    SELECT COUNT(*) FROM failed_login_attempts
                    WHERE attempt_time > ?
                """, (yesterday,))
                recent_failed_logins = cursor.fetchone()[0]

                # Audit events in last 24 hours
                cursor.execute("""
                    SELECT COUNT(*) FROM audit_trail
                    WHERE timestamp > ?
                """, (yesterday,))
                recent_audit_events = cursor.fetchone()[0]

                # Data access events in last 24 hours
                cursor.execute("""
                    SELECT COUNT(*) FROM data_access_log
                    WHERE timestamp > ?
                """, (yesterday,))
                recent_data_access = cursor.fetchone()[0]

                return {
                    'active_sessions': active_sessions,
                    'failed_logins_24h': recent_failed_logins,
                    'audit_events_24h': recent_audit_events,
                    'data_access_24h': recent_data_access,
                    'security_policy': {
                        'session_timeout_minutes': self.policy.session_timeout_minutes,
                        'max_failed_logins': self.policy.max_failed_logins,
                        'data_retention_days': self.policy.data_retention_days
                    }
                }

        except Exception as e:
            self.logger.error(f"Error getting security metrics: {e}")
            return {}

    # Private helper methods

    def _get_current_user_id(self) -> Optional[int]:
        """Get current user ID from session context (placeholder)"""
        # This would typically get the user ID from the current session/request context
        # Implementation depends on your web framework (Flask, Django, etc.)
        # For now, return None - this should be implemented based on your session management
        return None

    def _get_user_access_level(self, user_id: int) -> AccessLevel:
        """Get user's access level"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT role FROM users WHERE id = ?
                """, (user_id,))

                result = cursor.fetchone()

                if result:
                    role = result[0]
                    if role == 'admin':
                        return AccessLevel.ADMIN
                    elif role == 'coach':
                        return AccessLevel.COACH
                    else:
                        return AccessLevel.USER

                return AccessLevel.USER

        except Exception as e:
            self.logger.error(f"Error getting user access level: {e}")
            return AccessLevel.USER

    def _has_permission(self, user_id: int, permission_type: str, resource_id: int = None) -> bool:
        """Check if user has specific permission"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM user_permissions
                    WHERE user_id = ? AND permission_type = ?
                    AND (resource_id = ? OR resource_id IS NULL)
                    AND is_active = 1
                    AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                """, (user_id, permission_type, resource_id))

                count = cursor.fetchone()[0]
                return count > 0

        except Exception as e:
            self.logger.error(f"Error checking permission: {e}")
            return False

    def _log_data_access(self, user_id: int, resource_type: str, access_type: str,
                        accessed_user_id: int = None, resource_id: int = None, ip_address: str = None):
        """Log data access event"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO data_access_log
                    (user_id, accessed_user_id, resource_type, resource_id, access_type, ip_address)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, accessed_user_id, resource_type, resource_id, access_type, ip_address))

                conn.commit()

        except Exception as e:
            self.logger.error(f"Error logging data access: {e}")


class SecurityError(Exception):
    """Custom security exception"""
    pass


# Global security service instance
security_service = SecurityService()


# Convenience decorators for common use cases
def require_authentication(func):
    """Require user authentication"""
    return security_service.require_user_access()(func)

def require_admin(func):
    """Require admin access"""
    return security_service.require_user_access([AccessLevel.ADMIN])(func)

def require_coach_or_admin(func):
    """Require coach or admin access"""
    return security_service.require_user_access([AccessLevel.COACH, AccessLevel.ADMIN])(func)

def require_own_data(data_user_id_param: str = 'user_id'):
    """Require user to access only their own data"""
    return security_service.require_data_ownership(data_user_id_param)
