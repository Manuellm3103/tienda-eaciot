"""Customer support tickets."""
from datetime import datetime
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.support_ticket import SupportTicket


class SupportService:
    async def create_ticket(
        self,
        db: AsyncSession,
        email: str,
        subject: str,
        message: str,
        name: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> SupportTicket:
        ticket = SupportTicket(
            email=email,
            subject=subject,
            message=message,
            name=name,
            user_id=user_id,
        )
        db.add(ticket)
        await db.flush()
        return ticket

    async def list_tickets(
        self, db: AsyncSession, status: Optional[str] = None, limit: int = 100
    ) -> List[SupportTicket]:
        query = select(SupportTicket).order_by(SupportTicket.created_at.desc()).limit(limit)
        if status:
            query = query.where(SupportTicket.status == status)
        result = await db.execute(query)
        return result.scalars().all()

    async def get_ticket(self, db: AsyncSession, ticket_id: str) -> Optional[SupportTicket]:
        return await db.get(SupportTicket, ticket_id)

    async def update_status(
        self,
        db: AsyncSession,
        ticket_id: str,
        status: str,
        admin_notes: Optional[str] = None,
    ) -> Optional[SupportTicket]:
        ticket = await self.get_ticket(db, ticket_id)
        if not ticket:
            return None
        ticket.status = status
        if admin_notes is not None:
            ticket.admin_notes = admin_notes
        if status == "resolved":
            ticket.resolved_at = datetime.utcnow()
        await db.flush()
        return ticket


support_service = SupportService()
