"""
Base service class for progression-related services
Contains shared functionality and common methods
"""

import logging
from typing import Optional
from models.database.connection_manager import get_db_manager

logger = logging.getLogger(__name__)


class BaseProgressionService:
    """Base class for all progression services"""

    def __init__(self, user_id: Optional[int] = None, connection_manager=None):
        self.user_id = user_id
        self.connection_manager = connection_manager or get_db_manager()
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_connection(self):
        """Get database connection from connection manager"""
        return self.connection_manager.get_connection()

    def set_user_id(self, user_id: int):
        """Set or update the user ID"""
        self.user_id = user_id

    def validate_user_id(self) -> bool:
        """Validate that user_id is set and valid"""
        if not self.user_id or self.user_id <= 0:
            self.logger.error(f"Invalid user_id: {self.user_id}")
            return False
        return True

    def validate_exercise_id(self, exercise_id: int) -> bool:
        """Validate that exercise_id is valid"""
        if not exercise_id or exercise_id <= 0:
            self.logger.error(f"Invalid exercise_id: {exercise_id}")
            return False
        return True
