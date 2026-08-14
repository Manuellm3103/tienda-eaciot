import pytest
from sqlalchemy import create_engine
from app.database import _ensure_sqlite_columns


def _cols(conn, table):
    return {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()}


def test_sqlite_column_migration_adds_missing_columns():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        # Simulate an OLD schema: orders without customer_rfc/uso_cfdi.
        conn.exec_driver_sql(
            "CREATE TABLE orders (id VARCHAR(36) PRIMARY KEY, total_amount NUMERIC)"
        )
        _ensure_sqlite_columns(conn)
        cols = _cols(conn, "orders")
        assert "customer_rfc" in cols
        assert "uso_cfdi" in cols
    engine.dispose()


def test_sqlite_column_migration_is_idempotent():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE order_items (id VARCHAR(36) PRIMARY KEY, quantity INTEGER)"
        )
        _ensure_sqlite_columns(conn)
        # Second pass must be a no-op (no duplicate column error).
        _ensure_sqlite_columns(conn)
        cols = _cols(conn, "order_items")
        assert "variant_id" in cols
        assert "variant_name" in cols
    engine.dispose()
