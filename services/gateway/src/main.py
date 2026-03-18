"""
API Gateway Service - FastAPI
Entry point for all microservices. Handles authentication, rate limiting, and routing.
"""

import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional

import httpx
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

# Configuration
REDIS_URL = "redis://redis:6379"
RATE_LIMIT_REQUESTS = 100
RATE_LIMIT_WINDOW = 60

# Service routing map
SERVICES = {
    "job-matching": "http://job-matching:8001",
    "notification": "http://notification:8002",
    "payment": "http://payment:8003",
}

# Redis client
redis_client: Optional[redis.Redis] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global redis_client
    try:
        redis_client = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
    except Exception as e:
        print(f"Warning: Redis connection failed: {e}")
        redis_client = None
    yield
    if redis_client:
        await redis_client.close()


app = FastAPI(
    title="API Gateway",
    description="Central entry point for microservices",
    version="1.0.0",
    lifespan=lifespan,
)


async def check_rate_limit(client_id: str) -> bool:
    """Sliding window rate limiting using Redis."""
    if not redis_client:
        return True  # Allow if Redis unavailable
    
    key = f"rate_limit:{client_id}"
    try:
        current = await redis_client.get(key)
        if current is None:
            await redis_client.setex(key, RATE_LIMIT_WINDOW, 1)
            return True
        
        count = int(current)
        if count >= RATE_LIMIT_REQUESTS:
            return False
        
        await redis_client.incr(key)
        return True
    except Exception:
        return True  # Fail open


@app.middleware("http")
async def gateway_middleware(request: Request, call_next):
    """Request middleware for tracing and rate limiting."""
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    request.state.correlation_id = correlation_id
    
    client_id = request.headers.get("X-API-Key") or request.client.host if request.client else "unknown"
    
    if not await check_rate_limit(client_id):
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"error": "Rate limit exceeded", "retry_after": RATE_LIMIT_WINDOW},
            headers={"X-Correlation-ID": correlation_id},
        )
    
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    response.headers["X-Correlation-ID"] = correlation_id
    response.headers["X-Response-Time"] = f"{process_time:.3f}s"
    
    return response


async def proxy_to_service(service_name: str, path: str, request: Request):
    """Proxy request to appropriate microservice."""
    if service_name not in SERVICES:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
    
    service_url = SERVICES[service_name]
    target_url = f"{service_url}{path}"
    
    headers = dict(request.headers)
    headers["X-Correlation-ID"] = request.state.correlation_id
    if request.client:
        headers["X-Forwarded-For"] = request.client.host
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            body = await request.body()
            response = await client.request(
                method=request.method,
                url=target_url,
                headers={k: v for k, v in headers.items() if k.lower() not in ['host', 'content-length']},
                content=body,
            )
            return JSONResponse(
                content=response.json() if response.content else {},
                status_code=response.status_code,
                headers={"X-Correlation-ID": request.state.correlation_id},
            )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service '{service_name}' is currently unavailable",
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Service '{service_name}' timed out",
        )


@app.get("/health")
async def health_check():
    """Gateway health status."""
    redis_healthy = False
    if redis_client:
        try:
            await redis_client.ping()
            redis_healthy = True
        except:
            pass
    
    return {
        "status": "healthy" if redis_healthy else "degraded",
        "service": "gateway",
        "redis": "connected" if redis_healthy else "disconnected",
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Gateway Event Horizon - API Gateway",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# Proxy routes
@app.api_route("/job-matching/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def job_matching_proxy(path: str, request: Request):
    """Proxy to Job Matching Service."""
    return await proxy_to_service("job-matching", f"/job-matching/{path}", request)


@app.api_route("/notifications/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def notification_proxy(path: str, request: Request):
    """Proxy to Notification Service."""
    return await proxy_to_service("notification", f"/notifications/{path}", request)


@app.api_route("/payments/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def payment_proxy(path: str, request: Request):
    """Proxy to Payment Service."""
    return await proxy_to_service("payment", f"/payments/{path}", request)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
