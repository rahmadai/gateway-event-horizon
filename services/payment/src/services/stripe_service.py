"""
Stripe payment service.
"""

import os
from typing import Optional, Dict, Any
import hashlib
import hmac


class StripeService:
    """Stripe payment processing service."""
    
    def __init__(self):
        self.secret_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_dummy")
        self.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_dummy")
        self.test_mode = not self.secret_key.startswith("sk_live")
    
    def construct_event(
        self,
        payload: bytes,
        sig_header: str
    ) -> Dict[str, Any]:
        """
        Verify webhook signature and construct event.
        
        Args:
            payload: Request body
            sig_header: Stripe-Signature header value
            
        Returns:
            Event dictionary
            
        Raises:
            ValueError: If signature verification fails
        """
        if self.webhook_secret == "whsec_dummy":
            # In test mode, skip verification
            import json
            return json.loads(payload)
        
        # Verify signature
        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Parse signature header
        # Format: t=timestamp,v1=signature
        try:
            parts = sig_header.split(",")
            sig_dict = {}
            for part in parts:
                key, value = part.split("=")
                sig_dict[key] = value
            
            if sig_dict.get("v1") != expected_signature:
                raise ValueError("Invalid signature")
            
            import json
            return json.loads(payload)
            
        except Exception as e:
            raise ValueError(f"Signature verification failed: {e}")
    
    def create_payment_intent(
        self,
        amount: int,
        currency: str,
        customer_id: str,
        payment_method: str,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a payment intent.
        
        In production, this would call Stripe API.
        For demo, it simulates the response.
        """
        if self.test_mode:
            # Simulate Stripe response
            import os
            pi_id = f"pi_{os.urandom(12).hex()}"
            return {
                "id": pi_id,
                "object": "payment_intent",
                "amount": amount,
                "currency": currency,
                "customer": customer_id,
                "payment_method": payment_method,
                "status": "succeeded",
                "client_secret": f"{pi_id}_secret_{os.urandom(12).hex()}",
            }
        
        # Production would use stripe library:
        # import stripe
        # stripe.api_key = self.secret_key
        # return stripe.PaymentIntent.create(...)
        
        raise NotImplementedError("Stripe library not installed")
    
    def create_refund(
        self,
        payment_intent_id: str,
        amount: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a refund."""
        if self.test_mode:
            import os
            return {
                "id": f"re_{os.urandom(12).hex()}",
                "object": "refund",
                "amount": amount or 0,
                "payment_intent": payment_intent_id,
                "status": "succeeded",
            }
        
        raise NotImplementedError("Stripe library not installed")


# Global instance
stripe_service = StripeService()
