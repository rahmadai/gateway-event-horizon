"""
Authentication models for Gateway.
"""

from typing import Optional, List
from pydantic import BaseModel


class TokenRequest(BaseModel):
    """Token request."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    refresh_token: Optional[str] = None


class User(BaseModel):
    """User model."""
    id: int
    username: str
    email: str
    is_active: bool = True
    roles: List[str] = []


class RateLimitInfo(BaseModel):
    """Rate limit information."""
    limit: int
    remaining: int
    reset_at: str
