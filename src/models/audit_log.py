from sqlalchemy import Column, String, JSON, Integer
from sqlalchemy.sql.sqltypes import DateTime
from sqlalchemy.types import Enum

from .base import Base, TimestampMixin
from datetime import datetime, timezone
from src.schemas.enums import LogSeverity, LogAction


class AuditLog(Base, TimestampMixin):
    """Model for storing audit logs."""

    __tablename__ = "audit_logs"

    # Composite primary key for TimescaleDB partitioning
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), primary_key=True, default=lambda: datetime.now(timezone.utc), nullable=False)
    tenant_id = Column(Integer, primary_key=True, nullable=False)
    user_id = Column(String, nullable=False, index=True)
    session_id = Column(String, nullable=False)
    action = Column(Enum(LogAction), nullable=False)
    resource_type = Column(String, nullable=False)
    resource_id = Column(String, nullable=False)
    ip_address = Column(String, nullable=False)
    user_agent = Column(String, nullable=False)
    message = Column(String, nullable=False)
    log_metadata = Column(JSON, nullable=True)
    before_state = Column(JSON, nullable=True)
    after_state = Column(JSON, nullable=True)
    severity = Column(Enum(LogSeverity), nullable=False)

    # created_at is now part of the primary key above

    def __repr__(self):
        return f"tenant_id={self.tenant_id}, action={self.action})"
