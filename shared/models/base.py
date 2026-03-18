"""
Base Pydantic models shared across services.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TimestampedModel(BaseModel):
    """Base model with timestamp fields."""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class HealthResponse(BaseModel):
    """Standard health check response."""
    status: str
    service: str
    version: str = "1.0.0"


class PaginatedResponse(BaseModel):
    """Standard paginated response wrapper."""
    items: list
    total: int
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    pages: int = 1
