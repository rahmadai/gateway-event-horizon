"""
Email notification models.
"""

from typing import List, Optional
from pydantic import BaseModel, EmailStr
from enum import Enum


class EmailPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class EmailAttachment(BaseModel):
    """Email attachment model."""
    filename: str
    content_type: str
    content: str  # base64 encoded


class EmailRequest(BaseModel):
    """Email sending request."""
    to_addresses: List[EmailStr]
    subject: str
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    from_address: Optional[str] = None
    cc_addresses: Optional[List[EmailStr]] = None
    bcc_addresses: Optional[List[EmailStr]] = None
    attachments: Optional[List[EmailAttachment]] = None
    priority: EmailPriority = EmailPriority.NORMAL
    template_id: Optional[str] = None
    template_variables: Optional[dict] = None


class EmailResponse(BaseModel):
    """Email sending response."""
    message_id: str
    status: str  # queued, sent, failed
    recipient_count: int
    queued_at: str


class EmailTemplate(BaseModel):
    """Email template model."""
    id: str
    name: str
    subject_template: str
    body_text_template: Optional[str] = None
    body_html_template: Optional[str] = None
    variables: List[str] = []
