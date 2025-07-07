from datetime import datetime

from pydantic import BaseModel, ConfigDict
from typing import Optional


class TenantBase(BaseModel):
    """Base tenant schema."""
    name: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TenantCreate(TenantBase):
    """Schema for creating a tenant."""
    pass


class TenantUpdate(TenantBase):
    """Schema for updating a tenant."""
    name: Optional[str] = None
    description: Optional[str] = None


class Tenant(TenantBase):
    """Schema for tenant."""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, model):
        """Convert SQLAlchemy model to a Pydantic model."""
        return cls.model_validate(model)
