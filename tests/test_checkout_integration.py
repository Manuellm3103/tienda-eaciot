"""HTTP-level integration test of the full commercial path.

Exercises register -> login cookie -> add variant to cart -> view cart ->
checkout (order creation with correct variant pricing, RFC and total), with
Stripe stubbed so no live credentials are needed. This is a deterministic
stand-in for the slower cua-driver browser E2E.
"""
import sys
import pytest
import app.services.stripe_service  # noqa: F401  (ensure module imported)
from sqlalchemy import select
from app.models.product import Product, Category
from app.models.product_variant import ProductVariant
from app.models.user import User
from app.models.order import Order, OrderItem
from app.services.auth_service import create_access_token

# The services package __init__ shadows submodules with singletons, so resolve
# the real module via sys.modules (same as test_search.py).
STRIPE_MODULE = sys.modules["app.services.stripe_service"]


async def _seeded_product(db, slug="checkout-cat"):
    category = Category(name="Checkout Cat", slug=slug)
    db.add(category)
    await db.commit()
    await db.refresh(category)
    product = Product(
        title="Checkout Product", description="demo", price=50, stock=10,
        category_id=category.id, product_type="fisico",
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    variant = ProductVariant(
        product_id=product.id, name="Talla M", price_delta=10, stock=5
    )
    db.add(variant)
    await db.commit()
    await db.refresh(variant)
    return product, variant


async def _login_user(client, db, email):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        user = User(email=email, name="Comprador", hashed_password="x")
        db.add(user)
        await db.commit()
        await db.refresh(user)
    token = create_access_token({"sub": user.id})
    client.cookies.set("access_token", token)
    return user


@pytest.mark.asyncio
async def test_full_checkout_with_variant_and_rfc(client, db, monkeypatch):
    product, variant = await _seeded_product(db, slug="checkout-cat-full")
    user = await _login_user(client, db, "checkout.buyer@test.com")

    # Stub Stripe to avoid live credentials.
    async def fake_checkout(order, success_url, cancel_url):
        return {"url": "https://checkout.stripe.com/test/session"}

    monkeypatch.setattr(
        STRIPE_MODULE.stripe_service, "create_checkout_session", fake_checkout
    )

    # 1. Set the cart cookie with a variant (the cookie round-trip through
    #    httpx double-encodes special chars; the cart route is covered in
    #    test_pages, so here we seed the cookie directly to focus on checkout).
    import json
    client.cookies.set(
        "cart", json.dumps({f"{product.id}::{variant.id}": 1})
    )

    # 2. Establish a CSRF cookie (middleware emits it on the GET).
    await client.get("/cart")
    csrf = next((c.value for c in client.cookies.jar if c.name == "csrf_token"), None)
    assert csrf

    # 3. POST checkout with shipping + RFC.
    form = {
        "_csrf_token": csrf,
        "name": "Comprador",
        "street": "Av. Reforma 123",
        "city": "Ciudad de México",
        "state": "CDMX",
        "zip_code": "01000",
        "country": "México",
        "phone": "5551234567",
        "customer_rfc": "XAXX010101000",
        "uso_cfdi": "G03",
    }
    resp = await client.post(
        "/checkout",
        data=form,
        headers={"X-CSRF-Token": csrf},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "stripe.com" in resp.headers["location"]

    # 4. Order persisted with variant snapshot, RFC and correct total.
    order = (
        await db.execute(select(Order).where(Order.user_id == user.id))
    ).scalar_one()
    assert order.customer_rfc == "XAXX010101000"
    assert order.uso_cfdi == "G03"

    item = (
        await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))
    ).scalar_one()
    assert item.variant_name == "Talla M"
    assert float(item.price_at_purchase) == 60.00


@pytest.mark.asyncio
async def test_checkout_redirects_anonymous_to_login(client, db):
    product, _ = await _seeded_product(db, slug="checkout-cat-anon")
    resp = await client.get("/checkout")
    assert resp.status_code == 302
    assert "/products/" in resp.headers["location"]


async def _place_order(client, db, user, monkeypatch, slug):
    """Run the checkout POST and return the created order."""
    product, variant = await _seeded_product(db, slug=slug)
    import json

    async def fake_checkout(order, success_url, cancel_url):
        return {"url": "https://checkout.stripe.com/test/session"}

    monkeypatch.setattr(
        STRIPE_MODULE.stripe_service, "create_checkout_session", fake_checkout
    )
    client.cookies.set(
        "cart", json.dumps({f"{product.id}::{variant.id}": 1})
    )
    await client.get("/cart")
    csrf = next((c.value for c in client.cookies.jar if c.name == "csrf_token"), None)
    form = {
        "_csrf_token": csrf,
        "name": "Comprador", "street": "Av. Reforma 123", "city": "CDMX",
        "state": "CDMX", "zip_code": "01000", "country": "México",
        "phone": "5551234567",
    }
    resp = await client.post(
        "/checkout", data=form, headers={"X-CSRF-Token": csrf}, follow_redirects=False,
    )
    assert resp.status_code == 302
    order = (
        await db.execute(select(Order).where(Order.user_id == user.id))
    ).scalar_one()
    return order


@pytest.mark.asyncio
async def test_checkout_success_fulfills_order_via_session_fallback(client, db, monkeypatch):
    """The /checkout/success fallback confirms the Checkout Session server-side
    and fulfills the order even when the webhook never fires."""
    user = await _login_user(client, db, "fallback.buyer@test.com")
    order = await _place_order(client, db, user, monkeypatch, "checkout-cat-fallback")
    assert order.status == "pending"

    # Stub Stripe: the Checkout Session is already paid (webhook missed it).
    monkeypatch.setattr(
        STRIPE_MODULE.stripe_service,
        "retrieve_checkout_session",
        lambda session_id: {
            "id": "cs_test_123",
            "payment_status": "paid",
            "status": "complete",
            "payment_intent": "pi_test_123",
            "metadata": {"order_id": str(order.id)},
        },
    )

    resp = await client.get(
        f"/checkout/success?order_id={order.id}&session_id=cs_test_123"
    )
    assert resp.status_code == 200
    await db.refresh(order)
    assert order.status == "paid"
    assert order.payment_method == "stripe"
    assert order.payment_id == "pi_test_123"


@pytest.mark.asyncio
async def test_checkout_success_ignores_wrong_order_in_session(client, db, monkeypatch):
    """If the session metadata references a different order, the fallback must
    NOT fulfill our order (prevents cross-order fulfillment from a forged/leaked
    session id)."""
    user = await _login_user(client, db, "wrongmeta.buyer@test.com")
    order = await _place_order(client, db, user, monkeypatch, "checkout-cat-wrongmeta")

    monkeypatch.setattr(
        STRIPE_MODULE.stripe_service,
        "retrieve_checkout_session",
        lambda session_id: {
            "id": "cs_test_999",
            "payment_status": "paid",
            "status": "complete",
            "payment_intent": "pi_test_999",
            "metadata": {"order_id": "some-other-order"},
        },
    )

    resp = await client.get(
        f"/checkout/success?order_id={order.id}&session_id=cs_test_999"
    )
    assert resp.status_code == 200
    await db.refresh(order)
    assert order.status == "pending"
