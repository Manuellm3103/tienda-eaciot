from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.database import get_db
from app.services.chat_service import chat_service


router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatMessage(BaseModel):
    message: str


@router.post("/")
async def chat(request: Request, data: ChatMessage, db: AsyncSession = Depends(get_db)):
    """AI shopping assistant endpoint."""
    result = await chat_service.chat(db, data.message)
    return JSONResponse(result)


@router.get("/")
async def chat_get(request: Request, message: str, db: AsyncSession = Depends(get_db)):
    """AI shopping assistant via GET (for no-JS / quick testing)."""
    result = await chat_service.chat(db, message)
    return JSONResponse(result)
