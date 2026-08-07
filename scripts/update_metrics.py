#!/usr/bin/env python3
"""Update dashboard metrics - runs via cron hourly"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import async_session
from app.services.dashboard_service import dashboard_service


async def update_metrics():
    """Update dashboard metrics"""
    async with async_session() as db:
        try:
            metrics = await dashboard_service.get_dashboard_metrics(db)
            print(f"Metrics updated: {metrics['sales']['total']} total sales")
        except Exception as e:
            print(f"Error updating metrics: {e}")


if __name__ == "__main__":
    asyncio.run(update_metrics())
