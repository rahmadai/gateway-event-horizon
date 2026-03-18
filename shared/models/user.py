"""
User-related shared models.
"""

from typing import List, Optional
from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    """Base user model."""
    email: EmailStr
    name: Optional[str] = None
    phone: Optional[str] = None


class User(UserBase):
    """Full user model."""
    id: int
    is_active: bool = True
    roles: List[str] = []
    
    class Config:
        from_attributes = True


class UserPreferences(BaseModel):
    """User notification preferences."""
    email_enabled: bool = True
    sms_enabled: bool = False
    push_enabled: bool = True
    whatsapp_enabled: bool = False
