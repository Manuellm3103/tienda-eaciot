from fastapi import APIRouter, Depends, Request, Cookie
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional
from app.config import settings
from app.database import get_db
from app.services.chat_service import chat_service
from app.services.agent_memory import create_session_id
from app.dependencies import get_current_user_optional


router = APIRouter(prefix="/api/chat", tags=["chat"])


def _cookie_secure():
    """Use secure cookies only when HTTPS is expected."""
    return settings.force_https or settings.frontend_url.startswith("https://")


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
        secure=_cookie_secure(),
        samesite="lax",
        max_age=86400 * 30,
        path="/",
    )
    return response


@router.get("/")
async def chat_get(
    request: Request,
    message: str,
    session_id: Optional[str] = None,
    chat_session: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db),
):
    """AI shopping assistant via GET (for no-JS / quick testing)."""
    resolved = await _resolve_session_id(session_id, chat_session)
    user = await get_current_user_optional(request, db)
    result = await chat_service.chat(
        db, message, session_id=resolved, user_id=str(user.id) if user else None
    )
    response = JSONResponse(result)
    response.set_cookie(
        key="chat_session",
        value=resolved,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        max_age=86400 * 30,
        path="/",
    )
    return response
