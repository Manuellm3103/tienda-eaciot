import pytest
from sqlalchemy import select
from app.models.email_queue import EmailQueue
from app.services.email_queue_service import email_queue_service
from app.services.email_service import email_service


@pytest.mark.asyncio
async def test_enqueue_creates_pending_email(db):
    item = await email_queue_service.enqueue(
        db, to_email="a@test.com", subject="Hola", html_content="<b>x</b>"
    )
    await db.commit()
    assert item.status == "pending"
    assert item.to_email == "a@test.com"


@pytest.mark.asyncio
async def test_enqueue_dedupe_reuses_pending(db):
    first = await email_queue_service.enqueue(
        db, to_email="b@test.com", subject="VERIFY Hola",
        html_content="<b>1</b>", dedupe_key="VERIFY",
    )
    await db.flush()
    second = await email_queue_service.enqueue(
        db, to_email="b@test.com", subject="VERIFY Hola 2",
        html_content="<b>2</b>", dedupe_key="VERIFY",
    )
    assert second.id == first.id  # reused, not duplicated


@pytest.mark.asyncio
async def test_retry_failed(db):
    item = await email_queue_service.enqueue(
        db, to_email="c@test.com", subject="Fail", html_content="x"
    )
    item.status = "failed"
    item.attempts = 3
    await db.commit()
    ok = await email_queue_service.retry_failed(db, item.id)
    await db.commit()
    assert ok is True
    assert item.status == "pending"
    assert item.attempts == 0


def test_render_verification_email_is_self_contained():
    html = email_service.render_verification_email("Ana", "tok123")
    assert "Ana" in html
    assert "tok123" in html
    assert "Verificar Email" in html


def test_render_password_reset_email_is_self_contained():
    html = email_service.render_password_reset_email("Ana", "tok456")
    assert "Ana" in html
    assert "tok456" in html
    assert "Restablecer Contraseña" in html


@pytest.mark.asyncio
async def test_admin_email_queue_requires_admin(client):
    resp = await client.get("/admin/email-queue/list")
    assert resp.status_code in (401, 403)
