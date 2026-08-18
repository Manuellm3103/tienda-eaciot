import pytest
from sqlalchemy import select

from app.models.user import User
from app.models.supplier import Supplier
from app.models.app_setting import AppSetting
from app.services.auth_service import create_access_token


async def _auth_admin(client, db) -> None:
    result = await db.execute(select(User).where(User.email == "supplier@test.com"))
    user = result.scalar_one_or_none()
    if not user:
        user = User(email="supplier@test.com", name="Admin", is_admin=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    token = create_access_token({"sub": user.id})
    client.cookies.set("access_token", token)


@pytest.mark.asyncio
async def test_suppliers_requires_admin(client, db):
    resp = await client.get("/admin/suppliers/")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_suppliers_crud(client, db):
    await _auth_admin(client, db)

    resp = await client.get("/admin/suppliers/")
    assert resp.status_code == 200
    assert "Proveedores" in resp.text
    csrf = client.cookies.get("csrf_token")
    assert csrf

    resp = await client.post(
        "/admin/suppliers/",
        data={"name": "Distribuidora HP Norte", "lead_time_days": "5"},
        headers={"X-CSRF-Token": csrf},
        follow_redirects=False,
    )
    assert resp.status_code == 302

    result = await db.execute(select(Supplier).where(Supplier.name == "Distribuidora HP Norte"))
    supplier = result.scalar_one_or_none()
    assert supplier is not None
    assert supplier.lead_time_days == 5


@pytest.mark.asyncio
async def test_llm_models_list_and_set(client, db):
    await _auth_admin(client, db)
    await client.get("/admin/dashboard")  # establece la cookie csrf
    csrf = client.cookies.get("csrf_token")
    assert csrf

    resp = await client.get("/admin/llm/models")
    assert resp.status_code == 200
    data = resp.json()
    assert "models" in data
    assert "current" in data
    assert "config" in data

    resp = await client.post(
        "/admin/llm/model",
        data={"provider": "opencode", "model": "qwen3.8-max"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    assert resp.json()["model"] == "qwen3.8-max"

    result = await db.execute(select(AppSetting).where(AppSetting.key == "llm_model"))
    row = result.scalar_one_or_none()
    assert row is not None
    assert row.value == "qwen3.8-max"


@pytest.mark.asyncio
async def test_llm_model_rejects_bad_provider(client, db):
    await _auth_admin(client, db)
    await client.get("/admin/dashboard")
    csrf = client.cookies.get("csrf_token")

    resp = await client.post(
        "/admin/llm/model",
        data={"provider": "evil", "model": "x"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 400
