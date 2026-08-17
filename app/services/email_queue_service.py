"""Transactional email outbox (cron-free).

`enqueue` drafts an email into EmailQueue and returns immediately; the request
then schedules `flush_pending()` as a fire-and-forget background task, so SMTP
delivery never blocks a customer action AND needs no Render cron (free tier
asks for a card to create cron jobs). The queue remains visible/retryable in
the admin outbox panel.
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_queue import EmailQueue


class EmailQueueService:
    async def enqueue(
        self,
        db: AsyncSession,
        to_email: str,
        subject: str,
        html_content: str,
        dedupe_key: Optional[str] = None,
    ) -> EmailQueue:
        """Queue an email. With a dedupe_key, a pending email sharing that key
        is reused instead of queued twice (idempotent resend)."""
        if dedupe_key:
            existing = (
                await db.execute(
                    select(EmailQueue)
                    .where(EmailQueue.to_email == to_email)
                    .where(EmailQueue.subject.like(f"%{dedupe_key}%"))
                    .where(EmailQueue.status == "pending")
                    .limit(1)
                )
            ).scalar_one_or_none()
            if existing:
                return existing

        item = EmailQueue(to_email=to_email, subject=subject, html_content=html_content)
        db.add(item)
        await db.flush()
        return item

    async def enqueue_and_flush(
        self,
        db: AsyncSession,
        to_email: str,
        subject: str,
        html_content: str,
        dedupe_key: Optional[str] = None,
    ) -> None:
        """Enqueue in the CURRENT request transaction (committed by get_db),
        then deliver in the background using its own session. No cron needed."""
        await self.enqueue(db, to_email, subject, html_content, dedupe_key)
        asyncio.get_running_loop().create_task(self._flush_after_commit())

    async def _flush_after_commit(self, limit: int = 10) -> int:
        """Deliver after the request transaction commits.

        enqueue_and_flush runs inside the request's transaction: the queued row
        only becomes visible to OTHER sessions after get_db commits (which
        happens after the response). A flush scheduled immediately would open
        its own session, see an empty queue and leave the email pending
        forever. Sleep first, and retry once if nothing went out (slow commit
        or transient SMTP failure).
        """
        await asyncio.sleep(1.0)
        sent = await self.flush_pending(limit)
        if sent == 0:
            await asyncio.sleep(3.0)
            sent = await self.flush_pending(limit)
        return sent

    async def flush_pending(self, limit: int = 10) -> int:
        """Deliver pending queued emails via SMTP (new session, own commit).

        Returns the number of emails processed. Failures are recorded with
        attempts+1 and left for the admin outbox retry button."""
        from app.database import async_session
        from app.services.email_service import email_service

        async with async_session() as db:
            rows = (
                await db.execute(
                    select(EmailQueue)
                    .where(EmailQueue.status == "pending")
                    .where(EmailQueue.attempts < 3)
                    .order_by(EmailQueue.created_at.asc())
                    .limit(limit)
                )
            ).scalars().all()

            sent = 0
            for item in rows:
                try:
                    ok = await email_service.send_email(
                        to_email=item.to_email,
                        subject=item.subject,
                        html_content=item.html_content,
                    )
                    if ok:
                        item.status = "sent"
                        item.sent_at = datetime.now(timezone.utc)
                        item.last_error = None
                        sent += 1
                    else:
                        item.attempts += 1
                        item.last_error = "SMTP send returned False"
                except Exception as exc:  # noqa: BLE001 — record, don't crash
                    item.attempts += 1
                    item.last_error = str(exc)[:255]

            await db.commit()
            return sent

    async def list_items(self, db: AsyncSession, limit: int = 100) -> list[dict]:
        rows = (
            await db.execute(
                select(EmailQueue).order_by(EmailQueue.created_at.desc()).limit(limit)
            )
        ).scalars().all()
        return [
            {
                "id": str(r.id),
                "to_email": r.to_email,
                "subject": r.subject,
                "status": r.status,
                "attempts": r.attempts,
                "last_error": r.last_error,
                "sent_at": r.sent_at.isoformat() if r.sent_at else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]

    async def retry_failed(self, db: AsyncSession, email_id: str) -> bool:
        item = await db.get(EmailQueue, email_id)
        if not item:
            return False
        item.status = "pending"
        item.attempts = 0
        item.last_error = None
        await db.flush()
        return True


email_queue_service = EmailQueueService()
