from typing import Optional
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.services.auth_service import decode_token


async def get_current_user_optional(request: Request, db: AsyncSession) -> Optional[User]:
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = decode_token(token)
    if not payload or not payload.get("sub"):
        return None
    result = await db.execute(select(User).where(User.id == payload["sub"]))
    return result.scalar_one_or_none()
