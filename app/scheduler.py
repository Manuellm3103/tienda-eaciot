"""Lightweight asyncio scheduler for autonomous marketing campaigns.

No external cron/APScheduler dependency: two long-lived tasks are created at
application startup. They sleep until their next trigger, run the campaign
engine, and then sleep again.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.database import get_db_session
from app.services.campaign_engine import campaign_engine

logger = logging.getLogger(__name__)


async def _sleep_until(target: datetime) -> None:
    now = datetime.now(timezone.utc)
    delay = (target - now).total_seconds()
    if delay > 0:
        await asyncio.sleep(delay)


async def _run_every(interval_seconds: int, fn) -> None:
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            async with get_db_session() as db:
                await fn(db)
        except Exception as exc:  # noqa: BLE001 — keep scheduler alive
            logger.exception("Scheduler periodic task failed: %s", exc)


async def _daily_at(hour: int, minute: int, fn) -> None:
    while True:
        now = datetime.now(timezone.utc)
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        await _sleep_until(target)
        try:
            async with get_db_session() as db:
                await fn(db)
        except Exception as exc:  # noqa: BLE001 — keep scheduler alive
            logger.exception("Scheduler daily task failed: %s", exc)
        # Sleep a little so we don't run twice in the same minute.
        await asyncio.sleep(60)


async def start_scheduler() -> None:
    if not settings.scheduler_enabled:
        return

    # Every 30 minutes: detect abandoned carts and convert them into campaigns.
    asyncio.create_task(_run_every(1800, campaign_engine.detect_abandoned_carts))

    # Daily at 09:00: create seasonal campaigns for upcoming Mexican holidays.
    asyncio.create_task(
        _daily_at(9, 0, campaign_engine.create_seasonal_campaigns_for_today)
    )
