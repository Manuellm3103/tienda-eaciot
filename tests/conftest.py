import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.database import Base, get_db
from app.main import app
from httpx import AsyncClient, ASGITransport

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


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
