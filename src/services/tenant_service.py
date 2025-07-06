from typing import List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Tenant


class TenantService:
    """Service class for handling tenant management operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_tenants(self) -> Sequence[Tenant]:
        """
        List all tenants

        Returns:
            List[Tenant]: List of accessible tenants
        """
        result = await self.db.execute(select(Tenant))
        return result.scalars().all()

    async def create_tenant(self, tenant_data: dict) -> Tenant:
        """
        Create a new tenant.

        Args:
            tenant_data (dict): Tenant data to create

        Returns:
            Tenant: Created tenant
        """

        db_tenant = Tenant(**tenant_data)
        self.db.add(db_tenant)
        await self.db.commit()
        await self.db.refresh(db_tenant)
        return db_tenant
