"""API endpoints for searching audit logs."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from src.core import config
from src.core.auth import get_current_user, role_required
from src.schemas import AuditLogSearch, User, UserRole
from src.services.search_service import SearchService

router = APIRouter(prefix="/logs")
logger = logging.getLogger(__name__)

settings = config.get_settings()


@router.post(
    "/search",
    description="Search audit logs using full-text search",
    dependencies=[Depends(role_required(UserRole.AUDITOR))],
)
async def search_logs(
    search: AuditLogSearch, current_user: User = Depends(get_current_user), page: int = 1, limit: int = 100
):
    """
    Search audit logs using full-text search.

    Args:
        search (AuditLogSearch): Search parameters
        current_user (User): Current authenticated user
        page (int): Page number
        limit (int): Number of results per page

    Returns:
        JSONResponse: Search results
    """
    search_service = SearchService()
    try:
        # Convert filters to dictionary
        filters = search.filters.model_dump() if search.filters else {}

        results = await search_service.search_logs(
            tenant_id=current_user.tenant_id, query=search.query, filters=filters, page=page, limit=limit
        )

        return JSONResponse({"total": len(results), "results": results})
    except Exception as e:
        # logger.exception(f"Search failed: {str(e)}")
        logger.exception(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Search failed")
