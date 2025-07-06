"""Common enums for the API."""

from enum import Enum

class LogSeverity(str, Enum):
    """Enum for log severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class LogAction(str, Enum):
    """Enum for log actions."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    VIEW = "view"
