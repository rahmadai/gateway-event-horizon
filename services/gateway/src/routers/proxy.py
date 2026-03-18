"""
Proxy router for gateway.
"""

from fastapi import APIRouter, Request, HTTPException
import httpx

router = APIRouter()


async def proxy_request(service_url: str, path: str, request: Request):
    """Proxy request to backend service."""
    target_url = f"{service_url}{path}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        body = await request.body()
        response = await client.request(
            method=request.method,
            url=target_url,
            headers=dict(request.headers),
            content=body,
        )
        return response.json()
