from typing import Optional
from fastapi import Request, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.services.auth_service import decode_token


def cookie_secure(request: Optional[Request] = None) -> bool:
    """Whether cookies should carry the Secure flag.

    Authoritative signals (production):
    * FORCE_HTTPS=true (set in render.yaml / Render dashboard), OR
    * the request arrived over https.

    Behind Render's TLS-terminating proxy the app may see scheme http, so also
    honor the standard X-Forwarded-Proto header. FRONTEND_URL is deliberately
    NOT used: it is https:// even during local HTTP dev and would break the
    session/cart cookies there.
    """
    if settings.force_https:
        return True
    if request is None:
        return False
    if request.url.scheme == "https":
        return True
    proto = request.headers.get("x-forwarded-proto", "")
    return proto.split(",")[0].strip().lower() == "https"


async def get_current_user_optional(request: Request, db: AsyncSession) -> Optional[User]:
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = decode_token(token)
    if not payload or not payload.get("sub"):
        return None
    result = await db.execute(select(User).where(User.id == payload["sub"]))
    return result.scalar_one_or_none()


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    """Require an authenticated user, otherwise raise 401."""
    user = await get_current_user_optional(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


class LoginRequired(HTTPException):
    """Anonymous browser hit a protected page.

    FastAPI exception handlers DO propagate through the middleware stack
    (returning a Response from a plain dependency does NOT — the handler
    still runs and silently discards it, leaking the page). The app registers
    a handler that converts this into a 303 redirect to the login page.
    """


def _wants_html(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return "text/html" in accept or not accept


async def require_admin(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    """Require an authenticated admin user, otherwise raise 401/403.

    Anonymous browsers hitting admin pages are redirected to the login page
    (with a `next` param) instead of seeing a bare 401; API/JSON callers keep
    the 401/403 status.
    """
    user = await get_current_user_optional(request, db)
    if not user:
        if request.url.path.startswith("/api/") or not _wants_html(request):
            raise HTTPException(status_code=401, detail="Not authenticated")
        raise LoginRequired(status_code=401, detail="Not authenticated")
    if not getattr(user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Admin required")
    return user
