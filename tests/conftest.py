import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.database import Base, get_db
from app.main import app
from app.config import settings
from httpx import AsyncClient, ASGITransport

# Disable the background scheduler during tests so it does not create campaigns
# or enqueue emails unexpectedly while the suite runs.
settings.scheduler_enabled = False

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest_asyncio.fixture(autouse=True)
async def reset_rate_limiter():
    """Reset the in-memory rate limiter between tests so the global request
    budget is not exhausted by previous tests."""
    from app.middleware.rate_limit import rate_limiter

    rate_limiter.requests.clear()
    yield
    rate_limiter.requests.clear()


@pytest_asyncio.fixture(autouse=True)
async def clean_accumulated_test_data(db):
    """Truncate tables that accumulate rows across tests so each test sees
    only the data it creates."""
    yield
    from sqlalchemy import text

    await db.execute(text("PRAGMA foreign_keys=OFF"))
    await db.execute(text("DELETE FROM user_events"))
    await db.execute(text("DELETE FROM product_analytics"))
    await db.execute(text("DELETE FROM saved_reports"))
    await db.execute(text("DELETE FROM agent_actions"))
    await db.execute(text("DELETE FROM fraud_scores"))
    await db.execute(text("DELETE FROM campaigns"))
    await db.execute(text("DELETE FROM email_queue"))
    await db.execute(text("PRAGMA foreign_keys=ON"))
    await db.commit()


@pytest_asyncio.fixture(autouse=True)
async def no_background_email(monkeypatch):
    """Tests must not schedule real SMTP delivery or write to the real app.db.

    `enqueue_and_flush` is a fire-and-forget scheduler in production; replace it
    with a synchronous no-op so register/forgot-password don't spawn background
    tasks that would hit SendGrid or a different database."""
    from app.services import email_queue_service as eqs

    async def _noop(db, to_email, subject, html_content, dedupe_key=None):
        return None

    monkeypatch.setattr(eqs.email_queue_service, "enqueue_and_flush", _noop)


@pytest_asyncio.fixture(scope="session")
async def engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db(engine):
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture
async def client(db):
    async def override_get_db():
        yield db
    
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
