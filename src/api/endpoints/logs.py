"""API endpoints for managing audit logs."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.core import config
from src.core.auth import get_tenant_id
from src.core.validation import validate_pagination_params
from src.database import get_db
from src.schemas import AuditLog, AuditLogCreate, AuditLogFilter
from pydantic import BaseModel
from src.services.log_service import LogService

router = APIRouter(prefix="/logs")

settings = config.get_settings()


@router.post(
    "/",
    response_model=AuditLog,
    status_code=status.HTTP_201_CREATED,
    tags=["logs"],
    description="Create a new audit log entry"
)
# @require_role(UserRole.USER)
async def create_log(
    log: AuditLogCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new audit log entry.

    Args:
        db (Session): The database session
        log (AuditLogCreate): Log data to create

    Returns:
        AuditLog: Created audit log entry

    Raises:
        HTTPException: If user is not authorized
    """
    log_service = LogService(db)
    log_data = log.model_dump()
    result = await log_service.create_log(log_data)
    return AuditLog.from_model(result)


@router.get(
    "/",
    response_model=List[AuditLog],
    tags=["logs"],
    description="Get audit logs with filtering options"
)
# @require_role(UserRole.USER)
async def get_logs(
    log_filter: AuditLogFilter = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Get audit logs with filtering options.

    Args:
        log_filter (AuditLogFilter): Filtering parameters
        db:


    Returns:
        List[AuditLog]: List of audit logs
    """
    log_service = LogService(db)
    return await log_service.get_logs(
        tenant_id=log_filter.tenant_id,
        user_id=log_filter.user_id,
        resource_type=log_filter.resource_type,
        action=log_filter.action,
        severity=log_filter.severity,
        start_date=log_filter.start_date,
        end_date=log_filter.end_date,
    )


@router.get(
    "/{log_id}",
    response_model=AuditLog,
    tags=["logs"],
    description="Get a specific audit log entry"
)
# @require_role(UserRole.USER)
async def get_log_by_id(
    log_id: int,
    db: AsyncSession = Depends(get_db),
    # tenant_id: int = Depends(get_tenant_id),
):
    """
    Get a specific audit log entry.

    Args:
        db:
        log_id (int): ID of the log entry
        # tenant_id (int): Current tenant

    Returns:
        AuditLog: Audit log entry

    Raises:
        HTTPException: If log entry not found
    """
    log_service = LogService(db)
    log = await log_service.get_log_by_id(log_id)
    if log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Log entry not found"
        )
    return log
