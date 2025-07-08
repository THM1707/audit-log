"""Schemas for search functionality."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from .enums import LogSeverity, LogAction


class SearchFilter(BaseModel):
    """Search filter parameters."""
    user_id: Optional[str] = None
    resource_type: Optional[str] = None
    action: Optional[LogAction] = None
    severity: Optional[LogSeverity] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class AuditLogSearch(BaseModel):
    """Schema for audit log search parameters."""
    query: Optional[str] = Field(
        None,
        description="Search term for message and metadata content"
    )
    filters: Optional[SearchFilter] = Field(
        None,
        description="Additional filters for search"
    )
    sort_by: Optional[str] = Field(
        "created_at",
        description="Field to sort results by"
    )
    sort_direction: Optional[str] = Field(
        "desc",
        description="Sort direction (asc or desc)"
    )

    class Config:
        """Pydantic config."""
        from_attributes = True
        json_schema_extra = {
            "example": {
                "query": "error login failed",
                "filters": {
                    "severity": "ERROR",
                    "start_date": "2025-07-01T00:00:00",
                    "end_date": "2025-07-07T23:59:59"
                },
                "sort_by": "created_at",
                "sort_direction": "desc"
            }
        }
