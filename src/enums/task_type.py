"""Task types for background processing."""

from enum import Enum

class TaskType(str, Enum):
    """Enum for different types of background tasks."""
    INDEX_LOG = "INDEX_LOG"
    ARCHIVE_LOG = "ARCHIVE_LOG"
    
    def __str__(self) -> str:
        """Return string representation of the enum value."""
        return self.value
