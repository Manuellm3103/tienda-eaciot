#!/usr/bin/env python3
"""Cleanup expired sessions - runs via cron daily"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import async_session
from sqlalchemy import text


async def cleanup_sessions():
    """Remove expired sessions and tokens"""
    async with async_session() as db:
        try:
            # Clean expired verification tokens
            result = await db.execute(
                text("""
                    UPDATE users 
                    SET verification_token = NULL, 
                        verification_token_expires = NULL 
                    WHERE verification_token_expires < NOW()
                """)
            )
            print(f"Cleaned {result.rowcount} expired verification tokens")
            
            # Clean expired reset tokens
            result = await db.execute(
                text("""
                    UPDATE users 
                    SET reset_token = NULL, 
                        reset_token_expires = NULL 
                    WHERE reset_token_expires < NOW()
                """)
            )
            print(f"Cleaned {result.rowcount} expired reset tokens")
            
            # Clean old email queue entries
            result = await db.execute(
                text("""
                    DELETE FROM email_queue 
                    WHERE status = 'sent' 
                    AND sent_at < NOW() - INTERVAL '30 days'
                """)
            )
            print(f"Cleaned {result.rowcount} old email queue entries")
            
            await db.commit()
            
        except Exception as e:
            print(f"Error cleaning up: {e}")


if __name__ == "__main__":
    asyncio.run(cleanup_sessions())
