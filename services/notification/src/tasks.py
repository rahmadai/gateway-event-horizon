"""
Celery tasks for Notification Service - Email processing.
"""

import os
from celery import Celery
from typing import Dict, Any

# Celery configuration
broker_url = os.getenv("CELERY_BROKER_URL", "amqp://admin:admin@localhost:5672/")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

celery_app = Celery(
    "notification",
    broker=broker_url,
    backend=result_backend,
    include=["src.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    worker_prefetch_multiplier=1,
    task_routes={
        "src.tasks.send_email_task": {"queue": "email"},
        "src.tasks.send_bulk_email_task": {"queue": "email"},
    }
)


@celery_app.task(bind=True, max_retries=3)
def send_email_task(self, email_request: Dict[str, Any]):
    """
    Send email task via Celery.
    
    Retries:
        - 3 attempts total
        - Exponential backoff: 60s, 120s, 240s
    """
    try:
        # Import here to avoid circular imports
        from .services.email_service import email_service, EmailRequest
        
        # Reconstruct request
        request = EmailRequest(**email_request)
        
        # Send email
        result = email_service.send_email(request)
        
        if result.status == "failed":
            raise Exception("Email sending failed")
        
        return {
            "task_id": self.request.id,
            "message_id": result.message_id,
            "status": result.status,
            "recipient_count": result.recipient_count,
        }
        
    except Exception as exc:
        # Retry with exponential backoff
        countdown = 60 * (2 ** self.request.retries)
        print(f"[EMAIL TASK] Retrying in {countdown}s due to: {exc}")
        raise self.retry(exc=exc, countdown=countdown)


@celery_app.task(bind=True, max_retries=2)
def send_bulk_email_task(self, email_requests: list):
    """
    Process bulk email sending.
    """
    from .services.email_service import email_service, EmailRequest
    
    results = []
    failures = []
    
    for i, req_data in enumerate(email_requests):
        try:
            request = EmailRequest(**req_data)
            result = email_service.send_email(request)
            results.append(result.dict())
            
            # Small delay between emails to avoid rate limiting
            if i < len(email_requests) - 1:
                import time
                time.sleep(0.5)
                
        except Exception as e:
            failures.append({"index": i, "error": str(e)})
    
    return {
        "task_id": self.request.id,
        "total": len(email_requests),
        "sent": len(results),
        "failed": len(failures),
        "failures": failures,
    }


@celery_app.task
def process_webhook_notification(webhook_data: dict):
    """
    Process incoming webhook from email provider (e.g., SendGrid, SES).
    
    Handles:
    - Delivery confirmations
    - Bounce notifications
    - Spam reports
    """
    event_type = webhook_data.get("event")
    message_id = webhook_data.get("message_id")
    
    print(f"[WEBHOOK] {event_type} for message {message_id}")
    
    # In production, update database with delivery status
    # Could trigger retry for bounces, alert for spam, etc.
    
    return {
        "processed": True,
        "event_type": event_type,
        "message_id": message_id,
    }


@celery_app.task
def cleanup_old_notifications(days: int = 30):
    """
    Cleanup old notification records from database.
    """
    # In production, delete records older than specified days
    print(f"[CLEANUP] Removing notifications older than {days} days")
    
    return {
        "cleaned": 0,
        "days_threshold": days,
    }
