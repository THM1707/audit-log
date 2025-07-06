"""Base model definitions."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

def now_utc():
    return datetime.now(timezone.utc)

class TimestampMixin:
    """Mixin for adding timestamp fields."""

    created_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc, nullable=False)
