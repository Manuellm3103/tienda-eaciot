from fastapi import APIRouter, Depends, Request, Cookie, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional
from app.config import settings
from app.database import get_db
from app.services.chat_service import chat_service
from app.services.agent_memory import create_session_id
from app.dependencies import get_current_user_optional, cookie_secure
from app.middleware.rate_limit import RateLimiter


router = APIRouter(prefix="/api/chat", tags=["chat"])

# Cada mensaje invoca al LLM (costo real por llamada). Este endpoint es público
# (asistente de compras), así que limitamos por IP para evitar que un bot drene
# tokens. Bucket separado del rate-limit global de requests.
chat_rate_limiter = RateLimiter(requests_per_minute=15)


class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = Field(default=None, description="Existing chat session id")


async def _resolve_session_id(form_session: Optional[str], cookie_session: Optional[str]) -> str:
    return form_session or cookie_session or create_session_id()


@router.post("/")
async def chat(
    request: Request,
    data: ChatMessage,
    chat_session: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db),
):
    """AI shopping assistant endpoint. Returns a new/existing session cookie."""
    client_ip = request.client.host if request.client else "unknown"
    if not chat_rate_limiter.is_allowed(f"chat:{client_ip}"):
        raise HTTPException(
            status_code=429,
            detail="Demasiados mensajes. Intenta de nuevo en un momento.",
        )

    session_id = await _resolve_session_id(data.session_id, chat_session)
    user = await get_current_user_optional(request, db)
    result = await chat_service.chat(
        db, data.message, session_id=session_id, user_id=str(user.id) if user else None
    )
    response = JSONResponse(result)
    response.set_cookie(
        key="chat_session",
        value=session_id,
        httponly=True,
        secure=cookie_secure(request),
        samesite="lax",
        max_age=86400 * 30,
        path="/",
    )
    return response
