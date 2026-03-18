"""
Notification Service - FastAPI
Handles email notifications with SMTP support.
"""

import os
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr, Field
from enum import Enum
import redis.asyncio as redis

from .models.email import EmailRequest, EmailResponse, EmailPriority
from .services.email_service import email_service, render_template, EMAIL_TEMPLATES
from .tasks import send_email_task

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
cache: Optional[redis.Redis] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize connections."""
    global cache
    try:
        cache = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
        print("Notification Service: Connected to Redis")
    except Exception as e:
        print(f"Warning: Redis connection failed: {e}")
        cache = None
    yield
    if cache:
        await cache.close()
        print("Notification Service: Disconnected from Redis")


app = FastAPI(
    title="Notification Service",
    description="Email notification service with SMTP support",
    version="1.0.0",
    lifespan=lifespan,
)


class Channel(str, Enum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    PUSH = "push"
    SMS = "sms"


class NotificationRequest(BaseModel):
    """Generic notification request."""
    recipient: str
    channel: Channel
    template: str
    variables: dict = {}
    priority: str = "normal"


class SendEmailRequest(BaseModel):
    """Direct email sending request."""
    to: EmailStr
    subject: Optional[str] = None
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    template_id: Optional[str] = None
    template_variables: Optional[dict] = None
    priority: EmailPriority = EmailPriority.NORMAL


class BulkEmailRequest(BaseModel):
    """Bulk email request."""
    recipients: List[EmailStr]
    subject: str
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    template_id: Optional[str] = None
    template_variables: Optional[dict] = None


class TemplateResponse(BaseModel):
    """Template information response."""
    id: str
    name: str
    variables: List[str]


@app.get("/health")
async def health_check():
    """Service health check."""
    cache_healthy = False
    if cache:
        try:
            await cache.ping()
            cache_healthy = True
        except:
            pass
    
    smtp_configured = bool(
        os.getenv("SMTP_USER") and os.getenv("SMTP_PASSWORD")
    )
    
    return {
        "status": "healthy",
        "service": "notification",
        "cache": "connected" if cache_healthy else "disconnected",
        "smtp": "configured" if smtp_configured else "test_mode",
        "templates_available": len(EMAIL_TEMPLATES),
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Notification Service",
        "version": "1.0.0",
        "features": ["email_smtp", "templates", "bulk_sending"],
        "docs": "/docs"
    }


@app.get("/templates", response_model=List[TemplateResponse])
async def list_templates():
    """List available email templates."""
    return [
        TemplateResponse(
            id=t.id,
            name=t.name,
            variables=t.variables
        )
        for t in EMAIL_TEMPLATES.values()
    ]


@app.get("/templates/{template_id}")
async def get_template(template_id: str):
    """Get template details."""
    template = EMAIL_TEMPLATES.get(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {
        "id": template.id,
        "name": template.name,
        "subject_template": template.subject_template,
        "variables": template.variables,
    }


@app.post("/email/send", response_model=EmailResponse)
async def send_email(request: SendEmailRequest):
    """
    Send email directly.
    
    Either provide body_text/body_html directly or use a template.
    When using template_id, subject is extracted from template.
    """
    # Build email request
    email_req = EmailRequest(
        to_addresses=[request.to],
        subject=request.subject or "",
        body_text=request.body_text,
        body_html=request.body_html,
        priority=request.priority
    )
    
    # If template specified, render it
    if request.template_id:
        try:
            subject, text_body, html_body = render_template(
                request.template_id,
                request.template_variables or {}
            )
            email_req.subject = subject
            email_req.body_text = text_body
            email_req.body_html = html_body
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    # Validate we have content
    if not email_req.body_text and not email_req.body_html:
        raise HTTPException(
            status_code=400,
            detail="Either body_text, body_html, or template_id must be provided"
        )
    
    if not email_req.subject:
        raise HTTPException(status_code=400, detail="Subject is required")
    
    # Send email
    result = email_service.send_email(email_req)
    
    if result.status == "failed":
        raise HTTPException(status_code=500, detail="Failed to send email")
    
    return result


@app.post("/email/send-async", response_model=EmailResponse)
async def send_email_async(request: SendEmailRequest, background_tasks: BackgroundTasks):
    """
    Queue email for async sending via Celery.
    """
    # Build email request
    email_req = EmailRequest(
        to_addresses=[request.to],
        subject=request.subject or "",
        body_text=request.body_text,
        body_html=request.body_html,
        priority=request.priority
    )
    
    # If template specified, render it
    if request.template_id:
        try:
            subject, text_body, html_body = render_template(
                request.template_id,
                request.template_variables or {}
            )
            email_req.subject = subject
            email_req.body_text = text_body
            email_req.body_html = html_body
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    if not email_req.subject:
        raise HTTPException(status_code=400, detail="Subject is required")
    
    # Queue to Celery
    message_id = f"msg_{os.urandom(8).hex()}"
    
    # In production, this would be:
    # send_email_task.delay(email_req.dict())
    # For now, add to background tasks
    background_tasks.add_task(email_service.send_email, email_req)
    
    return EmailResponse(
        message_id=message_id,
        status="queued",
        recipient_count=1,
        queued_at="2024-01-15T10:30:00Z"
    )


@app.post("/email/bulk", response_model=EmailResponse)
async def send_bulk_emails(request: BulkEmailRequest):
    """
    Send email to multiple recipients.
    
    Note: In production, this should use Celery for large batches.
    """
    # For small batches, send directly
    # For large batches, use Celery
    
    sent_count = 0
    failed_count = 0
    
    for recipient in request.recipients[:10]:  # Limit to 10 for direct sending
        email_req = EmailRequest(
            to_addresses=[recipient],
            subject=request.subject,
            body_text=request.body_text,
            body_html=request.body_html
        )
        
        if request.template_id:
            try:
                subject, text_body, html_body = render_template(
                    request.template_id,
                    request.template_variables or {}
                )
                email_req.subject = subject
                email_req.body_text = text_body
                email_req.body_html = html_body
            except ValueError:
                failed_count += 1
                continue
        
        result = email_service.send_email(email_req)
        if result.status == "sent":
            sent_count += 1
        else:
            failed_count += 1
    
    return EmailResponse(
        message_id=f"bulk_{os.urandom(8).hex()}",
        status="sent" if failed_count == 0 else "partial",
        recipient_count=sent_count,
        queued_at="2024-01-15T10:30:00Z"
    )


@app.post("/notifications/send")
async def send_notification(request: NotificationRequest):
    """
    Generic notification endpoint - routes to appropriate channel.
    """
    if request.channel == Channel.EMAIL:
        # Render template and send email
        try:
            subject, text_body, html_body = render_template(
                request.template,
                request.variables
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        email_req = EmailRequest(
            to_addresses=[request.recipient],
            subject=subject,
            body_text=text_body,
            body_html=html_body
        )
        
        result = email_service.send_email(email_req)
        return {
            "notification_id": result.message_id,
            "channel": "email",
            "status": result.status,
            "recipient": request.recipient
        }
    
    elif request.channel == Channel.WHATSAPP:
        # Would integrate with WhatsApp Business API
        return {
            "notification_id": f"wa_{os.urandom(8).hex()}",
            "channel": "whatsapp",
            "status": "queued",
            "recipient": request.recipient
        }
    
    elif request.channel == Channel.SMS:
        # Would integrate with SMS gateway
        return {
            "notification_id": f"sms_{os.urandom(8).hex()}",
            "channel": "sms",
            "status": "queued",
            "recipient": request.recipient
        }
    
    else:
        raise HTTPException(status_code=400, detail=f"Channel {request.channel} not implemented")


@app.get("/notifications/{notification_id}/status")
async def get_notification_status(notification_id: str):
    """Get delivery status of a notification."""
    # In production, check Celery result backend or database
    return {
        "notification_id": notification_id,
        "status": "delivered",
        "delivered_at": "2024-01-15T10:30:00Z",
        "channel": "email",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
