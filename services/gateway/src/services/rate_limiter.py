"""
Rate limiting service.
"""

import redis.asyncio as redis
from typing import Optional


class RateLimiter:
    """Redis-based rate limiter."""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client
        self.default_limit = 100
        self.window = 60
    
    async def is_allowed(self, key: str, limit: Optional[int] = None) -> bool:
        """Check if request is allowed."""
        if not self.redis:
            return True
        
        limit = limit or self.default_limit
        current = await self.redis.get(f"rate_limit:{key}")
        
        if current is None:
            await self.redis.setex(f"rate_limit:{key}", self.window, 1)
            return True
        
        count = int(current)
        if count >= limit:
            return False
        
        await self.redis.incr(f"rate_limit:{key}")
        return True
    
    async def get_remaining(self, key: str) -> int:
        """Get remaining requests."""
        if not self.redis:
            return self.default_limit
        
        current = await self.redis.get(f"rate_limit:{key}")
        if current is None:
            return self.default_limit
        
        return max(0, self.default_limit - int(current))
