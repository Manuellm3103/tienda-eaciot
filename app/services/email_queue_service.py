"""Transactional email outbox.

`enqueue` drafts an email into EmailQueue and returns immediately — the SMTP
delivery is done later by scripts/process_emails.py (cron) or the admin retry
panel. Registration/password-reset use this so a slow SMTP server never blocks
a customer action.
"""
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
