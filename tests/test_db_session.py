import pytest
from app.database import get_db_session


@pytest.mark.asyncio
async def test_get_db_session_is_async_context_manager():
    """Regression: get_db_session must be usable with `async with`.

    It was missing the @asynccontextmanager decorator, which made
    StripeService.create_checkout_session crash on every checkout.
    """
    async with get_db_session() as db:
        from sqlalchemy import text

        result = await db.execute(text("SELECT 1"))
        assert result.scalar_one() == 1
