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


async def require_admin(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    """Require an authenticated admin user, otherwise raise 401/403."""
    user = await get_current_user(request, db)
    if not getattr(user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Admin required")
    return user
