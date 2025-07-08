from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core import config
from src.core.auth import role_required
from src.database.pool import get_db
from src.schemas import Tenant, TenantCreate, UserRole
from src.schemas.response import DataResponse
from src.services.tenant_service import TenantService

router = APIRouter(prefix="/tenants", tags=["Admin"])

settings = config.get_settings()


@router.get(
    "/",
    response_model=List[Tenant],
    description="List all accessible tenants",
    dependencies=[Depends(role_required(UserRole.ADMIN))],
)
async def list_tenants(
    db: AsyncSession = Depends(get_db),
) -> DataResponse[List[Tenant]]:
    """
    List all tenants. Only for Admins

    Returns:
        DataResponse[List[Tenant]]: List of all tenants
    """
    tenant_service = TenantService(db)
    return DataResponse(data=await tenant_service.list_tenants())


@router.post(
    "/",
    response_model=Tenant,
    status_code=status.HTTP_201_CREATED,
    description="Create a new tenant",
    dependencies=[Depends(role_required(UserRole.ADMIN))],
)
async def create_tenant(tenant: TenantCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new tenant
    Args:
        tenant (TenantCreate): The tenant to create
        db (AsyncSession): Database session

    Returns:
        DataResponse[Tenant]: Created tenant
    """
    tenant_service = TenantService(db)
    return DataResponse(data=await tenant_service.create_tenant(tenant.model_dump()))
