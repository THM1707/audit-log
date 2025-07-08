"""Base model definitions for SQLAlchemy 2.0 models."""

from datetime import datetime, timezone
from typing import Any, Callable, TypeVar, cast

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Type variable for declarative base
T = TypeVar("T", bound=datetime)


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.
    Provides automatic table naming and type annotation support.
    """

    pass


def now_utc() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


class TimestampMixin:
    """
    Mixin that adds timestamp fields to models.

    Attributes:
        created_at: When the record was created (auto-set on insert)
        updated_at: When the record was last updated (auto-updated)
    """

    __abstract__ = True

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when the record was created",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Timestamp when the record was last updated",
    )
