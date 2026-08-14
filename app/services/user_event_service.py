"""Lightweight behavioral-event recorder.

Analytics is a side concern: recording an event must never break the
user-facing request, so failures are swallowed and left for retries.
"""
import json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user_event import UserEvent


class UserEventService:
    async def record(
        self,
        db: AsyncSession,
        event_type: str,
        user_id: Optional[str] = None,
        product_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        try:
            db.add(
                UserEvent(
                    event_type=event_type,
                    user_id=user_id,
                    product_id=product_id,
                    session_id=session_id,
                    metadata_json=json.dumps(metadata) if metadata else None,
                )
            )
            await db.flush()
        except Exception:
            # Never break the user-facing flow because of analytics.
            pass


user_event_service = UserEventService()
