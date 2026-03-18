"""
Email service with SMTP support.
"""

import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional
from datetime import datetime
import base64

from ..models.email import EmailRequest, EmailResponse, EmailPriority, EmailTemplate


class EmailService:
    """SMTP email sending service."""
    
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_address = os.getenv("FROM_EMAIL", "notifications@example.com")
        self.use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    
    def _get_smtp_connection(self):
        """Create SMTP connection."""
        context = ssl.create_default_context()
        server = smtplib.SMTP(self.smtp_host, self.smtp_port)
        
        if self.use_tls:
            server.starttls(context=context)
        
        if self.smtp_user and self.smtp_password:
            server.login(self.smtp_user, self.smtp_password)
        
        return server
    
    def _build_message(self, request: EmailRequest) -> MIMEMultipart:
        """Build MIME message from request."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = request.subject
        msg["From"] = request.from_address or self.from_address
        msg["To"] = ", ".join(request.to_addresses)
        
        if request.cc_addresses:
            msg["Cc"] = ", ".join(request.cc_addresses)
        
        if request.bcc_addresses:
            msg["Bcc"] = ", ".join(request.bcc_addresses)
        
        # Priority header
        priority_map = {
            EmailPriority.LOW: "5",
            EmailPriority.NORMAL: "3",
            EmailPriority.HIGH: "2",
            EmailPriority.URGENT: "1"
        }
        msg["X-Priority"] = priority_map.get(request.priority, "3")
        
        # Add text body
        if request.body_text:
            msg.attach(MIMEText(request.body_text, "plain"))
        
        # Add HTML body
        if request.body_html:
            msg.attach(MIMEText(request.body_html, "html"))
        
        # Add attachments
        if request.attachments:
            for attachment in request.attachments:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(base64.b64decode(attachment.content))
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f'attachment; filename="{attachment.filename}"'
                )
                msg.attach(part)
        
        return msg
    
    def send_email(self, request: EmailRequest) -> EmailResponse:
        """
        Send email via SMTP.
        
        Args:
            request: Email request with all parameters
            
        Returns:
            EmailResponse with status and message ID
        """
        try:
            # Build message
            msg = self._build_message(request)
            message_id = f"msg_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{os.urandom(4).hex()}"
            msg["Message-ID"] = f"<{message_id}@gateway-event-horizon>"
            
            # Get all recipients
            recipients = request.to_addresses.copy()
            if request.cc_addresses:
                recipients.extend(request.cc_addresses)
            if request.bcc_addresses:
                recipients.extend(request.bcc_addresses)
            
            # Check if SMTP is configured
            if not self.smtp_user or not self.smtp_password:
                # In development, just log the email
                print(f"[EMAIL LOG] Would send email to: {recipients}")
                print(f"[EMAIL LOG] Subject: {request.subject}")
                print(f"[EMAIL LOG] Body: {request.body_text or request.body_html[:200]}")
                
                return EmailResponse(
                    message_id=message_id,
                    status="sent",
                    recipient_count=len(recipients),
                    queued_at=datetime.utcnow().isoformat()
                )
            
            # Send via SMTP
            with self._get_smtp_connection() as server:
                server.sendmail(
                    self.from_address,
                    recipients,
                    msg.as_string()
                )
            
            return EmailResponse(
                message_id=message_id,
                status="sent",
                recipient_count=len(recipients),
                queued_at=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            print(f"[EMAIL ERROR] Failed to send email: {e}")
            return EmailResponse(
                message_id=f"failed_{os.urandom(8).hex()}",
                status="failed",
                recipient_count=0,
                queued_at=datetime.utcnow().isoformat()
            )


# Templates
EMAIL_TEMPLATES = {
    "welcome": EmailTemplate(
        id="welcome",
        name="Welcome Email",
        subject_template="Welcome to {{service_name}}, {{name}}!",
        body_text_template="""
Hi {{name}},

Welcome to {{service_name}}! We're excited to have you on board.

Your account has been created with email: {{email}}

If you have any questions, please don't hesitate to contact us.

Best regards,
The {{service_name}} Team
        """.strip(),
        body_html_template="""
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #4CAF50; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to {{service_name}}!</h1>
        </div>
        <div class="content">
            <p>Hi {{name}},</p>
            <p>Welcome to {{service_name}}! We're excited to have you on board.</p>
            <p>Your account has been created with email: <strong>{{email}}</strong></p>
            <p>If you have any questions, please don't hesitate to contact us.</p>
        </div>
        <div class="footer">
            <p>Best regards,<br>The {{service_name}} Team</p>
        </div>
    </div>
</body>
</html>
        """.strip(),
        variables=["name", "email", "service_name"]
    ),
    "password_reset": EmailTemplate(
        id="password_reset",
        name="Password Reset",
        subject_template="Password Reset Request",
        body_text_template="""
Hi {{name}},

We received a request to reset your password. Click the link below to reset it:

{{reset_url}}

This link will expire in {{expiry_hours}} hours.

If you didn't request this, please ignore this email.

Best regards,
The {{service_name}} Team
        """.strip(),
        body_html_template="""
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .button { background: #2196F3; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Password Reset Request</h2>
        <p>Hi {{name}},</p>
        <p>We received a request to reset your password. Click the button below to reset it:</p>
        <p><a href="{{reset_url}}" class="button">Reset Password</a></p>
        <p>This link will expire in {{expiry_hours}} hours.</p>
        <p>If you didn't request this, please ignore this email.</p>
    </div>
</body>
</html>
        """.strip(),
        variables=["name", "reset_url", "expiry_hours", "service_name"]
    ),
    "booking_confirmation": EmailTemplate(
        id="booking_confirmation",
        name="Booking Confirmation",
        subject_template="Booking Confirmation - {{booking_type}} #{{booking_id}}",
        body_text_template="""
Hi {{customer_name}},

Your {{booking_type}} has been confirmed!

Booking Details:
- Booking ID: {{booking_id}}
- Date: {{booking_date}}
- Status: {{status}}

Thank you for choosing {{service_name}}.

Best regards,
The {{service_name}} Team
        """.strip(),
        variables=["customer_name", "booking_type", "booking_id", "booking_date", "status", "service_name"]
    )
}


def render_template(template_id: str, variables: dict) -> tuple:
    """
    Render email template with variables.
    
    Returns:
        Tuple of (subject, text_body, html_body)
    """
    template = EMAIL_TEMPLATES.get(template_id)
    if not template:
        raise ValueError(f"Template '{template_id}' not found")
    
    subject = template.subject_template
    text_body = template.body_text_template or ""
    html_body = template.body_html_template or ""
    
    # Simple template substitution
    for key, value in variables.items():
        placeholder = f"{{{{{key}}}}}"
        subject = subject.replace(placeholder, str(value))
        text_body = text_body.replace(placeholder, str(value))
        html_body = html_body.replace(placeholder, str(value))
    
    return subject, text_body, html_body


# Global instance
email_service = EmailService()
