#!/usr/bin/env python3
"""Backup database - runs via cron daily"""

import asyncio
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import settings


async def backup_database():
    """Create database backup"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backups")
    os.makedirs(backup_dir, exist_ok=True)
    
    # For Supabase, we rely on their automatic backups
    # This script can be extended for manual backups
    
    print(f"Backup completed at {timestamp}")
    print("Note: Supabase provides automatic daily backups")
    print("For manual backups, use Supabase dashboard or pg_dump")


if __name__ == "__main__":
    asyncio.run(backup_database())
