"""Tenant model definition."""
from typing import Dict, Any, Optional
from sqlalchemy import Text, Index
from sqlalchemy.dialects.mysql import VARCHAR
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class Tenant(Base, TimestampMixin):
    """Tenant model for multi-tenancy."""
    __tablename__ = "tenants"
    __table_args__ = (
        Index('idx_tenant_name', 'name', unique=True, postgresql_using='btree'),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    settings: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict, nullable=True)

    def __repr__(self) -> str:
        return f"Tenant(id={self.id}, name={self.name})"
