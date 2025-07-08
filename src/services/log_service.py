from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy import Row, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import AuditLog
from src.schemas import AuditLogCreate, LogAction, LogSeverity


class LogService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_log(self, log_data: dict) -> AuditLog:
        """Create a new audit log."""
        log = AuditLog(**log_data)
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log

    async def get_logs(
        self,
        tenant_id: int,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        action: Optional[LogAction] = None,
        severity: Optional[LogSeverity] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        limit: int = 100,
        as_json: bool = False,
    ) -> Sequence[AuditLog] | Sequence[Row[tuple[AuditLog]]]:
        """Get audit logs with filtering options.

        Args:
            tenant_id: Tenant ID to filter logs by
            user_id: Optional user ID to filter logs by
            resource_type: Optional resource type to filter logs by
            action: Optional log action to filter by (must be one of: CREATE, UPDATE, DELETE, VIEW)
            severity: Optional log severity to filter by (must be one of: INFO, WARNING, ERROR, CRITICAL)
            start_date: Optional start date to filter logs by
            end_date: Optional end date to filter logs by
            page: Page number for pagination
            limit: Number of items per page
            as_json: Return fetchall to make use of _asdict() method in result

        Returns:
            List of audit logs matching the filters
        """

        # using partitioning keys first
        stmt = select(AuditLog).where(AuditLog.tenant_id == tenant_id)
        if start_date:
            stmt = stmt.where(AuditLog.created_at >= start_date)
        if end_date:
            stmt = stmt.where(AuditLog.created_at <= end_date)

        if user_id:
            stmt = stmt.where(AuditLog.user_id == user_id)
        if resource_type:
            stmt = stmt.where(AuditLog.resource_type == resource_type)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if severity:
            stmt = stmt.where(AuditLog.severity == severity)
        offset = (page - 1) * limit
        stmt = stmt.offset(offset).limit(limit)

        result = await self.db.execute(stmt)
        if as_json:
            return result.fetchall()
        return result.scalars().all()

    async def get_log_by_id(self, log_id: int, tenant_id: int) -> Optional[AuditLog]:
        """Get a specific audit log entry by ID and tenant.

        Args:
            log_id: ID of the log entry to retrieve
            tenant_id: Tenant ID to filter by

        Returns:
            The audit log entry if found, None otherwise
        """

        # since timescale DB using tenant id as a dimension, we also use tenant_id to make use of partitioning
        stmt = select(AuditLog).where(AuditLog.id == log_id, AuditLog.tenant_id == tenant_id)

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_log_count(self, tenant_id: int | None = None) -> Optional[int]:
        query = select(func.count(AuditLog.id))
        if tenant_id:
            query = query.where(AuditLog.tenant_id == tenant_id)
        total_logs = await self.db.scalar(query)
        return total_logs
