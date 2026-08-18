from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from contextlib import asynccontextmanager
from app.config import settings


if settings.database_url.startswith("sqlite"):
    # SQLite async via aiosqlite
    engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
        connect_args={"check_same_thread": False},
    )
else:
    # PostgreSQL via asyncpg + Supabase/Pooler safe settings
    engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
        connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0},
    )

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_session() -> AsyncSession:
    """Standalone async context manager for database sessions."""
    session = async_session()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_ensure_sqlite_columns)


# ── Lightweight SQLite column migrations ─────────────────────────────────
# `create_all` only creates missing TABLES, never missing COLUMNS. On Render
# the SQLite file persists on the disk mount between deploys, so adding a
# column to an existing table would otherwise be silently skipped and break
# runtime queries. This idempotent shim backfills those columns safely.
_SQLITE_COLUMN_MIGRATIONS = {
    "users": [
        ("is_guest", "BOOLEAN DEFAULT 0"),
        ("favorite_category_id", "VARCHAR(36)"),
        ("phone", "VARCHAR(50)"),
        ("birthday", "TIMESTAMP"),
    ],
    "orders": [
        ("customer_rfc", "VARCHAR(20)"),
        ("uso_cfdi", "VARCHAR(10) DEFAULT 'G03'"),
    ],
    "order_items": [
        ("variant_id", "VARCHAR(36)"),
        ("variant_name", "VARCHAR(255)"),
    ],
    "invoices": [
        ("xml_content", "TEXT"),
    ],
    "products": [
        ("specs", "TEXT"),
        ("videos", "TEXT"),
        ("meta_title", "VARCHAR(255)"),
        ("meta_description", "TEXT"),
        ("content_generated_at", "TIMESTAMP"),
        ("content_score", "NUMERIC(5,2)"),
        ("seo_score", "NUMERIC(5,2)"),
        ("alt_texts", "TEXT"),
        ("base_price", "NUMERIC(10,2)"),
        ("compare_at_price", "NUMERIC(10,2)"),
        ("cost_price", "NUMERIC(10,2)"),
        ("hp_price", "NUMERIC(10,2)"),
        ("dynamic_price", "NUMERIC(10,2)"),
        ("dynamic_pricing_enabled", "BOOLEAN DEFAULT 0"),
        ("price_updated_at", "TIMESTAMP"),
        ("reorder_point", "INTEGER"),
        ("safety_stock_days", "INTEGER"),
    ],
    "reviews": [
        ("sentiment_score", "FLOAT"),
        ("sentiment_label", "VARCHAR(20)"),
        ("ai_response", "TEXT"),
        ("ai_response_approved", "BOOLEAN DEFAULT 0"),
        ("ai_responded_at", "TIMESTAMP"),
    ],
}


def _ensure_sqlite_columns(connection) -> None:
    """Add any missing columns to existing SQLite tables (idempotent)."""
    if not settings.database_url.startswith("sqlite"):
        return
    for table, columns in _SQLITE_COLUMN_MIGRATIONS.items():
        existing_rows = connection.exec_driver_sql(
            f"PRAGMA table_info({table})"
        ).fetchall()
        if not existing_rows:
            # Table doesn't exist yet (fresh DB) — create_all will make it.
            continue
        existing = {row[1] for row in existing_rows}
        for name, ddl in columns:
            if name not in existing:
                connection.exec_driver_sql(
                    f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"
                )
