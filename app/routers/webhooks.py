"""Public webhooks for external services.

Currently handles WhatsApp Cloud API verification and inbound message events.
"""

from fastapi import APIRouter, Request, HTTPException, Depends, Query
from fastapi.responses import PlainTextResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.services.whatsapp_service import whatsapp_service

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.get("/whatsapp")
async def verify_whatsapp(
    request: Request,
    hub_mode: str | None = Query(None, alias="hub.mode"),
    hub_verify_token: str | None = Query(None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(None, alias="hub.challenge"),
):
    """WhatsApp Cloud API subscription verification."""
    if hub_mode != "subscribe":
        raise HTTPException(status_code=400, detail="Invalid mode")
    if not settings.whatsapp_verify_token:
        raise HTTPException(status_code=403, detail="Webhook not configured")
    if hub_verify_token != settings.whatsapp_verify_token:
        raise HTTPException(status_code=403, detail="Invalid verify token")
    return PlainTextResponse(hub_challenge or "")


@router.post("/whatsapp")
async def receive_whatsapp(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Receive inbound WhatsApp messages and route them to the AI assistant."""
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc

    entries = payload.get("entry", []) if isinstance(payload, dict) else []
    for entry in entries:
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for message in value.get("messages", []):
                phone = message.get("from")
                text_obj = message.get("text", {})
                text = text_obj.get("body", "") if isinstance(text_obj, dict) else ""
                if phone and text:
                    await whatsapp_service.handle_incoming_message(db, phone, text)

    return JSONResponse({"status": "ok"})
