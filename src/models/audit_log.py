from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Enum

from .base import Base, TimestampMixin
from src.schemas.enums import LogAction, LogSeverity


class AuditLog(Base, TimestampMixin):
    """Audit log model for tracking system events."""

    __tablename__ = "audit_logs"

    # Indexes are now defined separately using __table_args__ as a dictionary
    __table_args__ = (
        # Regular indexes
        Index("idx_audit_logs_tenant_created", "tenant_id", "created_at", postgresql_using="btree"),
        Index("idx_audit_logs_tenant_user_created", "tenant_id", "user_id", "created_at", postgresql_using="btree"),
        Index("idx_audit_logs_tenant_action_created", "tenant_id", "action", "created_at", postgresql_using="btree"),
        Index(
            "idx_audit_logs_tenant_resource_type_created",
            "tenant_id",
            "resource_type",
            "created_at",
            postgresql_using="btree",
        ),
        Index(
            "idx_audit_logs_tenant_severity_created", "tenant_id", "severity", "created_at", postgresql_using="btree"
        ),
        Index("idx_audit_logs_created_at", "created_at", postgresql_using="brin"),
    )

    # Composite primary key for TimescaleDB partitioning
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
        default=func.now(),
        nullable=False,
        index=True,
        comment="Timestamp when the log was created",
    )
    # Log details
    user_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    session_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    action: Mapped[LogAction] = mapped_column(nullable=False)
    resource_type: Mapped[str] = mapped_column(Text, nullable=False)
    resource_id: Mapped[str] = mapped_column(Text, nullable=False)
    ip_address: Mapped[str] = mapped_column(Text, nullable=False)
    user_agent: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    log_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    before_state: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    after_state: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    severity: Mapped[LogSeverity] = mapped_column(
        Enum(LogSeverity), nullable=False, default=LogSeverity.INFO, index=True
    )

    def __repr__(self):
        return f"tenant_id={self.tenant_id}, action={self.action})"
