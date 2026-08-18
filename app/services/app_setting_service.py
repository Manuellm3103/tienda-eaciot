"""Key/value settings persisted in the database (survive restarts without a
redeploy). Used for runtime choices like the selected LLM model."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.app_setting import AppSetting


async def get_setting(db: AsyncSession, key: str, default: str = "") -> str:
    result = await db.execute(select(AppSetting).where(AppSetting.key == key))
    row = result.scalar_one_or_none()
    return row.value if row else default


async def set_setting(db: AsyncSession, key: str, value: str) -> None:
    result = await db.execute(select(AppSetting).where(AppSetting.key == key))
    row = result.scalar_one_or_none()
    if row:
        row.value = value
    else:
        db.add(AppSetting(key=key, value=value))
    await db.flush()
