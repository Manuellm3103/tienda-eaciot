"""Rate limiting middleware using in-memory storage (no Redis required)"""

from fastapi import Request, HTTPException
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio


class RateLimiter:
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = defaultdict(list)
    
    def _cleanup(self, key: str, window: int):
        """Remove expired requests"""
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=window)
        self.requests[key] = [
            req_time for req_time in self.requests[key] 
            if req_time > cutoff
        ]
    
    def is_allowed(self, key: str, window: int = 60) -> bool:
        """Check if request is allowed"""
        now = datetime.utcnow()
        self._cleanup(key, window)
        
        if len(self.requests[key]) >= self.requests_per_minute:
            return False
        
        self.requests[key].append(now)
        return True


# Global rate limiter instance
rate_limiter = RateLimiter(requests_per_minute=60)


async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware"""
    # Get client IP
    client_ip = request.client.host
    
    # Skip rate limiting for health checks
    if request.url.path == "/health":
        return await call_next(request)
    
    # Check rate limit
    if not rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later."
        )
    
    response = await call_next(request)
    return response
