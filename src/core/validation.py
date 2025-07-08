"""Validation utilities."""

from typing import Tuple

from fastapi import HTTPException, status


def validate_pagination_params(page: int, limit: int) -> Tuple[int, int]:
    """Validate pagination parameters.

    Args:
        page: Page number (must be >= 1)
        limit: Items per page (must be between 1 and 1000)

    Returns:
        Tuple[int, int]: Validated page and limit

    Raises:
        HTTPException: If parameters are invalid
    """
    if page < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Page must be at least 1")

    if limit < 1 or limit > 1000:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Limit must be between 1 and 1000")

    return page, limit
