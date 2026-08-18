import pytest
from sqlalchemy import select
from app.models.user import User
from app.models.product import Category, Product
from app.models.order import Order
from app.models.agent_action import AgentAction
from app.services.auth_service import create_access_token
from app.services.agents.checkout_agent import checkout_agent


async def _auth_client(client, db, email: str = "checkout@test.com", admin: bool = False) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        user = User(email=email, name="Checkout User", is_admin=admin)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    token = create_access_token({"sub": user.id})
    client.cookies.set("access_token", token)
    return user


async def _chat(client, message: str, session_id: str | None = None):
    body = {"message": message}
    if session_id:
        body["session_id"] = session_id
    return await client.post("/api/chat/", json=body)


@pytest.mark.asyncio
async def test_checkout_intent_starts_flow(client, db):
    await _auth_client(client, db)
    response = await _chat(client, "quiero comprar")
    assert response.status_code == 200
    data = response.json()
    assert "Vamos a crear tu pedido" in data["answer"]
    assert data["agent"] == "checkout"


@pytest.mark.asyncio
async def test_checkout_full_flow_creates_order(client, db):
    user = await _auth_client(client, db, email="checkoutflow@test.com")

    category = Category(name="Checkout", slug="checkout")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    product = Product(
        title="Zapatos Rojos",
        description="Desc",
        price=250,
        category_id=category.id,
        product_type="fisico",
        stock=10,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    session_id = "checkout-session-1"

    # Start
    r1 = await _chat(client, "quiero comprar", session_id=session_id)
    assert r1.json()["agent"] == "checkout"

    # Items
    r2 = await _chat(client, "2 zapatos rojos", session_id=session_id)
    assert "dirección" in r2.json()["answer"].lower()

    # Address
    r3 = await _chat(client, "Calle Principal 123, Cuernavaca", session_id=session_id)
    assert "Resumen" in r3.json()["answer"]

    # Confirm
    r4 = await _chat(client, "sí, comprar", session_id=session_id)
    data = r4.json()
    assert "Pedido creado" in data["answer"]
    assert data["metadata"]["order_id"]

    order_id = data["metadata"]["order_id"]
    order = (
        await db.execute(select(Order).where(Order.id == order_id))
    ).scalars().first()
    assert order is not None
    assert float(order.total_amount) == 500.0
    assert str(order.user_id) == str(user.id)

    actions = (
        await db.execute(select(AgentAction).where(AgentAction.session_id == session_id))
    ).scalars().all()
    assert any(a.action_type == "create_order" for a in actions)


@pytest.mark.asyncio
async def test_checkout_requires_auth(client, db):
    category = Category(name="CheckoutAnon", slug="checkoutanon")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    product = Product(
        title="Producto Anonimo",
        description="Desc",
        price=100,
        category_id=category.id,
        product_type="fisico",
        stock=10,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    session_id = "checkout-anon"
    await _chat(client, "quiero comprar", session_id=session_id)
    await _chat(client, "1 producto anonimo", session_id=session_id)
    await _chat(client, "direccion 123", session_id=session_id)
    response = await _chat(client, "sí, comprar", session_id=session_id)
    data = response.json()
    assert "iniciar sesión" in data["answer"].lower()


@pytest.mark.asyncio
async def test_checkout_spending_limit_escalates(client, db):
    user = await _auth_client(client, db, email="checkoutlimit@test.com")

    category = Category(name="CheckoutLimit", slug="checkoutlimit")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    product = Product(
        title="Producto Caro",
        description="Desc",
        price=3000,
        category_id=category.id,
        product_type="fisico",
        stock=10,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    session_id = "checkout-limit"
    await _chat(client, "quiero comprar", session_id=session_id)
    await _chat(client, "2 producto caro", session_id=session_id)
    response = await _chat(client, "direccion 123", session_id=session_id)
    assert "supera el límite" in response.json()["answer"].lower()


@pytest.mark.asyncio
async def test_checkout_cancel(client, db):
    await _auth_client(client, db, email="checkoutcancel@test.com")
    session_id = "checkout-cancel"
    await _chat(client, "quiero comprar", session_id=session_id)
    response = await _chat(client, "cancelar", session_id=session_id)
    assert "cancelado" in response.json()["answer"].lower()


@pytest.mark.asyncio
async def test_checkout_agent_class_method(client, db):
    user = await _auth_client(client, db, email="checkoutunit@test.com")
    category = Category(name="CheckoutUnit", slug="checkoutunit")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    product = Product(
        title="Libro Azul",
        description="Desc",
        price=150,
        category_id=category.id,
        product_type="fisico",
        stock=5,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    result = await checkout_agent.run(db, "quiero comprar", session_id="unit-1", user_id=user.id)
    assert "Vamos a crear" in result.answer

    result = await checkout_agent.run(db, "1 libro azul", session_id="unit-1", user_id=user.id)
    assert "dirección" in result.answer.lower()
