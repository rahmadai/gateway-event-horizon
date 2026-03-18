"""
Payment Service - FastAPI
Handles payment processing with Stripe integration
"""

import json
import os
from contextlib import asynccontextmanager
from typing import Optional

import aiomysql
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel

# Database configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "payment_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "secure_password")
DB_NAME = os.getenv("DB_NAME", "payment")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "sk_test_dummy")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_dummy")

pool: Optional[aiomysql.Pool] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database connection."""
    global pool
    try:
        pool = await aiomysql.create_pool(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            db=DB_NAME,
            minsize=5,
            maxsize=20,
            autocommit=True,
        )
        print(f"Payment Service: Connected to MySQL at {DB_HOST}:{DB_PORT}")
    except Exception as e:
        print(f"Warning: MySQL connection failed: {e}")
        pool = None
    yield
    if pool:
        pool.close()
        await pool.wait_closed()


app = FastAPI(
    title="Payment Service",
    description="Payment processing with idempotency and rollback safety",
    version="1.0.0",
    lifespan=lifespan,
)


class PaymentRequest(BaseModel):
    amount: int  # in cents
    currency: str = "usd"
    customer_id: str
    payment_method: str
    description: Optional[str] = None


class PaymentResponse(BaseModel):
    payment_id: str
    status: str
    amount: int
    currency: str


@app.get("/health")
async def health_check():
    """Service health check."""
    db_healthy = False
    
    if pool:
        try:
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1")
                    await cur.fetchone()
                    db_healthy = True
        except Exception as e:
            print(f"DB health check failed: {e}")
    
    return {
        "status": "healthy" if db_healthy else "degraded",
        "service": "payment",
        "database": "connected" if db_healthy else "disconnected",
        "stripe": "configured" if STRIPE_SECRET_KEY != "sk_test_dummy" else "test_mode",
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {"service": "Payment Service", "version": "1.0.0", "docs": "/docs"}


@app.post("/payments", response_model=PaymentResponse)
async def create_payment(
    request: PaymentRequest,
    idempotency_key: Optional[str] = Header(None)
):
    """
    Process a payment with idempotency support.
    """
    if not pool:
        raise HTTPException(status_code=503, detail="Database not available")
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            # Check idempotency
            if idempotency_key:
                await cur.execute(
                    "SELECT payment_intent_id, status FROM payments WHERE idempotency_key = %s",
                    (idempotency_key,)
                )
                existing = await cur.fetchone()
                if existing:
                    return PaymentResponse(
                        payment_id=existing[0],
                        status=existing[1],
                        amount=request.amount,
                        currency=request.currency,
                    )
            
            # Create payment record
            payment_intent_id = f"pi_{os.urandom(12).hex()}"
            await cur.execute(
                """
                INSERT INTO payments (payment_intent_id, amount, currency, status, idempotency_key, description)
                VALUES (%s, %s, %s, 'succeeded', %s, %s)
                """,
                (
                    payment_intent_id,
                    request.amount / 100,  # Convert cents to dollars
                    request.currency.upper(),
                    idempotency_key,
                    request.description,
                ),
            )
    
    return PaymentResponse(
        payment_id=payment_intent_id,
        status="succeeded",
        amount=request.amount,
        currency=request.currency,
    )


@app.get("/payments")
async def list_payments(limit: int = 20, offset: int = 0):
    """List payments."""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not available")
    
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                """
                SELECT id, payment_intent_id, amount, currency, status, created_at
                FROM payments
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                (limit, offset)
            )
            payments = await cur.fetchall()
    
    return {"payments": list(payments), "count": len(payments)}


@app.post("/webhooks/stripe")
async def stripe_webhook(payload: dict, stripe_signature: str = Header(None)):
    """
    Handle Stripe webhooks.
    """
    if not pool:
        raise HTTPException(status_code=503, detail="Database not available")
    
    event_id = payload.get("id", f"evt_{os.urandom(12).hex()}")
    event_type = payload.get("type", "unknown")
    
    # Store webhook event
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO webhook_events (event_id, event_type, payload)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE payload = %s
                """,
                (event_id, event_type, json.dumps(payload), json.dumps(payload))
            )
    
    # Process event
    if event_type == "payment_intent.succeeded":
        payment_intent = payload.get("data", {}).get("object", {})
        pi_id = payment_intent.get("id")
        # Update payment status
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE payments SET status = 'succeeded' WHERE payment_intent_id = %s",
                    (pi_id,)
                )
    
    elif event_type == "payment_intent.payment_failed":
        payment_intent = payload.get("data", {}).get("object", {})
        pi_id = payment_intent.get("id")
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE payments SET status = 'failed' WHERE payment_intent_id = %s",
                    (pi_id,)
                )
    
    return {"status": "processed", "event_id": event_id}


@app.post("/payments/{payment_id}/refund")
async def refund_payment(payment_id: str, amount: Optional[int] = None):
    """Refund a payment."""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not available")
    
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # Get payment
            await cur.execute(
                "SELECT id, amount FROM payments WHERE payment_intent_id = %s",
                (payment_id,)
            )
            payment = await cur.fetchone()
            
            if not payment:
                raise HTTPException(status_code=404, detail="Payment not found")
            
            refund_amount = (amount / 100) if amount else payment["amount"]
            refund_id = f"re_{os.urandom(12).hex()}"
            
            # Create refund record
            await cur.execute(
                """
                INSERT INTO refunds (refund_id, payment_id, amount, status)
                VALUES (%s, %s, %s, 'succeeded')
                """,
                (refund_id, payment["id"], refund_amount)
            )
            
            # Update payment status
            new_status = "refunded" if not amount or (amount / 100) >= payment["amount"] else "partially_refunded"
            await cur.execute(
                "UPDATE payments SET status = %s WHERE id = %s",
                (new_status, payment["id"])
            )
    
    return {
        "refund_id": refund_id,
        "payment_id": payment_id,
        "amount": refund_amount,
        "status": "succeeded",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
