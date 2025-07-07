"""API endpoints for managing audit logs."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core import config
from src.core.auth import role_required, get_current_user
from src.database import get_db
from src.schemas import AuditLog, AuditLogCreate, AuditLogFilter, UserRole, User
from src.services.log_service import LogService

router = APIRouter(prefix="/logs")

settings = config.get_settings()


@router.post(
    "/{tenant_id}/logs",
    response_model=AuditLog,
    status_code=status.HTTP_201_CREATED,
    description="Create a new audit log entry",
    dependencies=[Depends(role_required(UserRole.USER))],
)
async def create_log(
    tenant_id: int,
    log: AuditLogCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new audit log entry.

    Args:
        tenant_id (int): ID of the tenant
        log (AuditLogCreate): Data for the new audit log entry
        db (AsyncSession): Database session
        current_user (User): Current authenticated user

    Returns:
        AuditLog: Created audit log entry

    Raises:
        HTTPException: If user is not authorized or tenant ID doesn't match
    """
    compare_tenant_id(tenant_id, current_user.tenant_id)
    log_service = LogService(db)
    log_data = log.model_dump()
    log_data["session_data"] = current_user.model_dump()
    log_data["tenant_id"] = tenant_id
    log_data["user_id"] = current_user.id
    result = await log_service.create_log(log_data)
    return AuditLog.from_model(result)


@router.get(
    "/{tenant_id}/logs",
    response_model=List[AuditLog],
    description="Get audit logs with filtering options",
    dependencies=[Depends(role_required(UserRole.AUDITOR))],
)
async def get_logs(
    tenant_id: int,
    log_filter: AuditLogFilter = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get audit logs for a tenant with filtering options.

    Args:
        tenant_id (int): ID of the tenant to retrieve logs for
        log_filter (AuditLogFilter): Optional filtering parameters
        db (AsyncSession): Database session
        current_user (User): Current authenticated user

    Returns:
        List[AuditLog]: List of audit logs matching the filters

    Raises:
        HTTPException: If user is not authorized
    """
    compare_tenant_id(tenant_id, current_user.tenant_id)
    log_service = LogService(db)
    return await log_service.get_logs(
        tenant_id=current_user.tenant_id,
        user_id=log_filter.user_id,
        resource_type=log_filter.resource_type,
        action=log_filter.action,
        severity=log_filter.severity,
        start_date=log_filter.start_date,
        end_date=log_filter.end_date,
    )


@router.get(
    "/{tenant_id}/logs/{log_id}",
    response_model=AuditLog,
    description="Get a specific audit log entry",
    dependencies=[Depends(role_required(UserRole.AUDITOR))],
)
async def get_log_by_id(
    tenant_id: int,
    log_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific audit log entry.

    Args:
        current_user:session user
        db (AsyncSession): The database session
        log_id (int): ID of the log entry
        tenant_id (int): Current tenant

    Returns:
        AuditLog: Audit log entry

    Raises:
        HTTPException: If log entry not found
    """
    compare_tenant_id(tenant_id, current_user.tenant_id)
    log_service = LogService(db)
    log = await log_service.get_log_by_id(log_id, tenant_id)
    if log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Log entry not found"
        )
    return log


def compare_tenant_id(request_tenant_id: int, current_tenant_id: int) -> None:
    """
    Raise error if request tenant ID is different from current tenant ID
    """
    if request_tenant_id == current_tenant_id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"User of tenant ID {current_tenant_id} is not authorized to access this resource"
    )
