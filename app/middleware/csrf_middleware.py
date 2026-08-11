"""Middleware to ensure every response carries a CSRF token cookie."""
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.middleware.csrf import CSRF_COOKIE_NAME, get_csrf_token, set_csrf_cookie


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        token = get_csrf_token(request)
        request.state.csrf_token = token
        response = await call_next(request)
        if request.cookies.get(CSRF_COOKIE_NAME) != token:
            set_csrf_cookie(response, token, secure=request.url.scheme == "https")
        return response
