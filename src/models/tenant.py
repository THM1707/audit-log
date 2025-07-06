"""Tenant model definition."""
from sqlalchemy import Column, String, Integer

from .base import Base, TimestampMixin


class Tenant(Base, TimestampMixin):
    """Model for storing tenant information."""

    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)

    def __repr__(self):
        return f"Tenant(id={self.id}, name={self.name})"
