"""
Payment models.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel
from decimal import Decimal


class PaymentBase(BaseModel):
    """Base payment model."""
    amount: int  # in cents
    currency: str = "usd"
    customer_id: str
    description: Optional[str] = None


class PaymentCreate(PaymentBase):
    """Payment creation model."""
    payment_method: str
    idempotency_key: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class Payment(PaymentBase):
    """Full payment model."""
    id: int
    payment_intent_id: str
    status: str
    payment_method: Optional[str]
    idempotency_key: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class PaymentResponse(BaseModel):
    """Payment API response."""
    payment_id: str
    status: str
    amount: int
    currency: str
    client_secret: Optional[str] = None


class RefundRequest(BaseModel):
    """Refund request."""
    amount: Optional[int] = None  # Partial refund if specified
    reason: Optional[str] = None


class RefundResponse(BaseModel):
    """Refund response."""
    refund_id: str
    payment_id: str
    amount: float
    status: str


class WebhookEvent(BaseModel):
    """Webhook event model."""
    id: str
    type: str
    data: Dict[str, Any]
    created_at: Optional[datetime] = None
