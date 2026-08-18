"""Public webhooks for external services.

Currently handles WhatsApp Cloud API verification and inbound message events.
"""

import hashlib
import hmac
import json

from fastapi import APIRouter, Request, HTTPException, Depends, Query
from fastapi.responses import PlainTextResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.services.whatsapp_service import whatsapp_service

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _verify_whatsapp_signature(payload: bytes, sig_header: str) -> None:
    """Verify Meta's X-Hub-Signature-256 (HMAC-SHA256 of the RAW body).

    Meta firma el payload con el App Secret de la app de Meta (no el verify
    token ni el access token). Preferimos whatsapp_app_secret; si no está
    definido, caemos al access token para no romper integraciones previas.
    Fail-closed: sin secreto configurado, el webhook no acepta mensajes.
    """
    secret = settings.whatsapp_app_secret or settings.whatsapp_access_token
    if not secret:
        raise HTTPException(status_code=403, detail="Webhook not configured")
    expected = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig_header or "", expected):
        raise HTTPException(status_code=400, detail="Invalid signature")


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
    body = await request.body()
    _verify_whatsapp_signature(body, request.headers.get("X-Hub-Signature-256", ""))

    try:
        payload = json.loads(body)
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
