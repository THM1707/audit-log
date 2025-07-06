"""Database package for the Audit Log API.

This package provides database connection and initialization utilities.
"""

from .pool import get_db

__all__ = [
    'get_db',
]
