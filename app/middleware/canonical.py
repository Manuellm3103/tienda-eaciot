"""Canonical domain redirect middleware.

Enforces either www or non-www canonical host. Disabled when ALLOWED_HOSTS is '*'.
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import RedirectResponse

from app.config import settings


class CanonicalDomainMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        host = request.headers.get("host", "").lower().split(":")[0]
        allowed = settings.allowed_hosts_list

        if allowed == ["*"] or not allowed:
            return await call_next(request)

        canonical = allowed[0].lower()
        if host and host != canonical and canonical != "*":
            # Only redirect if the current host is in allowed list but not canonical.
            if host in [h.lower() for h in allowed]:
                url = request.url.replace(host=canonical)
                return RedirectResponse(url=str(url), status_code=301)

        return await call_next(request)
