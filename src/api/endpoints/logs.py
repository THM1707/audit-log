"""API endpoints for managing audit logs."""
import csv
import io
import json
from datetime import datetime
from typing import List, Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import Row
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse, StreamingResponse

from src.core import config
from src.core.auth import role_required, get_current_user
from src.database import get_db
from src.schemas import AuditLog, AuditLogCreate, AuditLogFilter, UserRole, User
from src.services.log_service import LogService

router = APIRouter(prefix="/logs")

settings = config.get_settings()


@router.post(
    "/",
    response_model=AuditLog,
    status_code=status.HTTP_201_CREATED,
    description="Create a new audit log entry",
    dependencies=[Depends(role_required(UserRole.USER))],
)
async def create_log(
    log: AuditLogCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new audit log entry.

    Args:
        log (AuditLogCreate): Data for the new audit log entry
        db (AsyncSession): Database session
        current_user (User): Current authenticated user

    Returns:
        AuditLog: Created audit log entry

    Raises:
        HTTPException: If user is not authorized or tenant ID doesn't match
    """
    log_service = LogService(db)
    log_data = log.model_dump()
    log_data["session_data"] = current_user.model_dump()
    log_data["tenant_id"] = current_user.tenant_id
    log_data["user_id"] = current_user.id
    result = await log_service.create_log(log_data)
    return AuditLog.from_model(result)


@router.get(
    "/",
    response_model=List[AuditLog],
    description="Get audit logs with filtering options",
    dependencies=[Depends(role_required(UserRole.AUDITOR))],
)
async def get_logs(
    log_filter: AuditLogFilter = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Sequence[AuditLog]:
    """
    Get audit logs for a tenant with filtering options.

    Args:
        log_filter (AuditLogFilter): Optional filtering parameters
        db (AsyncSession): Database session
        current_user (User): Current authenticated user

    Returns:
        List[AuditLog]: List of audit logs matching the filters

    Raises:
        HTTPException: If user is not authorized
    """
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
    "{log_id}",
    response_model=AuditLog,
    description="Get a specific audit log entry",
    dependencies=[Depends(role_required(UserRole.AUDITOR))],
)
async def get_log_by_id(
    log_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AuditLog:
    """
    Get a specific audit log entry.

    Args:
        current_user:session user
        db (AsyncSession): The database session
        log_id (int): ID of the log entry

    Returns:
        AuditLog: Audit log entry

    Raises:
        HTTPException: If log entry not found
    """
    log_service = LogService(db)
    log = await log_service.get_log_by_id(log_id, current_user.tenant_id)
    if log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Log entry not found"
        )
    return log


@router.get(
    "/export",
    tags=["export"],
    description="Export audit logs in CSV format",
    dependencies=[Depends(role_required(UserRole.AUDITOR))],

)
async def export_logs_csv(
    log_filter: AuditLogFilter = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export audit logs in CSV format and send to SQS queue.

    Args:
        log_filter (AuditLogFilter): Export filter parameters
        db (AsyncSession): Database session
        current_user (User): session_user

    Returns:
        JSONResponse: Export started successfully
    """
    # Get logs from the database
    log_service = LogService(db)
    logs: Sequence[AuditLog] = await log_service.get_logs(
        tenant_id=current_user.tenant_id,
        user_id=log_filter.user_id,
        resource_type=log_filter.resource_type,
        action=log_filter.action,
        severity=log_filter.severity,
        start_date=log_filter.start_date,
        end_date=log_filter.end_date,
    )

    # Create CSV buffer
    csv_buffer = io.StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames=[
        'id', 'tenant_id', 'created_at', 'user_id', 'session_data', 'action', 'resource_type',
        'resource_id', 'ip_address', 'user_agent', 'message', 'severity',
        'before_state', 'after_state', 'log_metadata',
    ])
    writer.writeheader()

    # Write logs to CSV
    for log in logs:
        writer.writerow({
            'id': log.id,
            'tenant_id': log.tenant_id,
            'created_at': log.created_at.isoformat(),
            'user_id': log.user_id,
            'session_data': json.dumps(log.session_data),
            'action': log.action,
            'resource_type': log.resource_type,
            'resource_id': log.resource_id,
            'ip_address': log.ip_address,
            'user_agent': log.user_agent,
            'message': log.message,
            'severity': log.severity,
            'before_state': json.dumps(log.before_state) if log.before_state else None,
            'after_state': json.dumps(log.after_state) if log.after_state else None,
            'log_metadata': json.dumps(log.log_metadata) if log.log_metadata else None
        })
    csv_buffer.seek(0)
    return StreamingResponse(
        csv_buffer,
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=audit_logs_{datetime.now().strftime('%Y%m%d')}.csv"
        }
    )


@router.get(
    "/export/json",
    tags=["export"],
    description="Export audit logs in JSON format"
)
async def export_logs_json(
    log_filter: AuditLogFilter = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export audit logs in JSON format

    Args:
        log_filter (AuditLogFilter): Export filter parameters
        db (AsyncSession): Database session
        current_user (User): session_user

    Returns:
        JSONResponse: Export started successfully
    """
    # Get logs from the database
    log_service = LogService(db)
    logs: Sequence[Row[tuple[AuditLog]]] = await log_service.get_logs(
        tenant_id=current_user.tenant_id,
        user_id=log_filter.user_id,
        resource_type=log_filter.resource_type,
        action=log_filter.action,
        severity=log_filter.severity,
        start_date=log_filter.start_date,
        end_date=log_filter.end_date,
        as_json=True
    )

    validate_export_limit(len(logs))

    output = io.StringIO()
    json.dump([log._asdict() for log in logs], output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=audit_logs_{datetime.now().strftime('%Y%m%d')}.json"
        }
    )


def validate_export_limit(log_count: int) -> None:
    """
    Validate that the export size is within allowed limits.

    Args:
        log_count (int): Number of logs

    Raises:
        ValueError: If export size exceeds the allowed limit
    """
    if log_count > config.get_settings().EXPORT_MAX_ROWS:
        raise ValueError(
            f"Export size exceeds maximum allowed rows ({config.get_settings().EXPORT_MAX_ROWS})"
        )
