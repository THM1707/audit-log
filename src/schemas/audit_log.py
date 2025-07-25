"""Audit log schemas."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict

from .enums import LogAction, LogSeverity


class AuditLogBase(BaseModel):
    """Base audit log schema."""

    action: LogAction
    resource_type: str
    resource_id: str
    ip_address: str
    user_agent: str
    message: str
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None
    log_metadata: Optional[Dict[str, Any]] = None
    severity: LogSeverity = "info"


class AuditLogCreate(AuditLogBase):
    """Schema for creating audit logs."""

    pass


class AuditLog(AuditLogBase):
    """Schema for audit logs."""

    id: int
    tenant_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, model):
        """Convert SQLAlchemy model to a Pydantic model."""
        return cls.model_validate(model)


class AuditLogFilter(BaseModel):
    """Schema for filtering audit logs."""

    user_id: Optional[str] = None
    resource_type: Optional[str] = None
    action: Optional[LogAction] = None
    severity: Optional[LogSeverity] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = 1
    limit: int = 100

    @classmethod
    def from_model(cls, model):
        """Convert SQLAlchemy model to a Pydantic model."""
        return cls.model_validate(model)
