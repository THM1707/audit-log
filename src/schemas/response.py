# app/schemas/response.py
from datetime import datetime, timezone
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

# Define a generic type for the data payload
T = TypeVar("T")


class Pagination(BaseModel):
    total_items: int = Field(..., description="Total number of items available.")
    page: int = Field(..., description="Current page number.")
    page_size: int = Field(..., description="Number of items per page.")
    total_pages: int = Field(..., description="Total number of pages.")


class BaseResponse(BaseModel):
    """Base response model for common fields."""

    status: str = Field(..., description="Status of the response (e.g., 'success', 'error').")
    message: Optional[str] = Field(None, description="A human-readable message about the response.")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of the response in UTC."
    )


class DataResponse(BaseResponse, Generic[T]):
    """Universal success response template."""

    status: str = "success"
    data: T = Field(None, description="The main data payload of the response.")
    pagination: Optional[Pagination] = Field(None, description="Pagination metadata for list responses.")


class MessageResponse(BaseResponse):
    """Simple success response for actions that don't return data."""

    status: str = "success"
    message: str = Field(..., description="A human-readable message about the action.")


class ErrorDetail(BaseModel):
    field: Optional[str] = Field(None, description="The field that caused the error (if applicable).")
    message: str = Field(..., description="A detailed message about the error.")
    code: Optional[str] = Field(None, description="An application-specific error code.")


class ErrorResponse(BaseResponse):
    status: str = "error"
    code: Optional[str] = Field(None, description="An application-specific error code.")
    errors: List[ErrorDetail] = Field([], description="List of detailed error messages.")
