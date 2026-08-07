#!/usr/bin/env python3
"""Process email queue - runs via cron every 5 minutes"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import async_session
from app.services.email_service import email_service
from sqlalchemy import text


async def process_pending_emails():
    """Process pending emails from queue"""
    async with async_session() as db:
        # Get pending emails
        result = await db.execute(
            text("""
                SELECT id, to_email, subject, html_content 
                FROM email_queue 
                WHERE status = 'pending' 
                AND attempts < 3 
                ORDER BY created_at ASC 
                LIMIT 10
            """)
        )
        emails = result.fetchall()
        
        for email_id, to_email, subject, html_content in emails:
            try:
                # Send email
                success = await email_service.send_email(
                    to_email=to_email,
                    subject=subject,
                    html_content=html_content
                )
                
                if success:
                    # Mark as sent
                    await db.execute(
                        text("UPDATE email_queue SET status = 'sent', sent_at = NOW() WHERE id = :id"),
                        {"id": email_id}
                    )
                else:
                    # Increment attempts
                    await db.execute(
                        text("UPDATE email_queue SET attempts = attempts + 1, last_error = 'Send failed' WHERE id = :id"),
                        {"id": email_id}
                    )
            except Exception as e:
                # Log error
                await db.execute(
                    text("UPDATE email_queue SET attempts = attempts + 1, last_error = :error WHERE id = :id"),
                    {"id": email_id, "error": str(e)[:255]}
                )
        
        await db.commit()
        print(f"Processed {len(emails)} emails")


if __name__ == "__main__":
    asyncio.run(process_pending_emails())
