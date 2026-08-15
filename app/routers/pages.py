import json
import uuid
import base64
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.models.product import Product, Category
from app.models.product_variant import ProductVariant
from app.models.order import Order
from app.models.promotion import Promotion
from app.schemas.order import OrderCreate, OrderItemCreate
from app.schemas.shipping import ShippingAddressCreate
from app.dependencies import get_current_user_optional, require_admin
from app.services.user_event_service import user_event_service
from app.services.product_service import product_service
from app.services.recommendation_service import recommendation_service
from app.services.variant_service import variant_service
from app.services.order_service import order_service
from app.services.promotion_service import promotion_service
from app.services.stripe_service import stripe_service
from app.services.shipping_service import shipping_service
from app.services.search_service import search_service
from app.middleware import validate_csrf
from app.config import settings

router = APIRouter(tags=["pages"])
from app.templates_instance import templates


def get_cart_from_cookie(request: Request) -> dict:
    cart_val = request.cookies.get("cart", "")
    if not cart_val:
        return {}
    # The HTTP cookie layer (and some clients like http.cookiejar) may wrap the
    # value in double quotes — strip them before decoding.
    cart_val = cart_val.strip().strip('"')
    # New format: base64(urlsafe) of JSON — immune to cookie-value quoting.
    try:
        raw = base64.urlsafe_b64decode(cart_val.encode("ascii")).decode("utf-8")
        cart = json.loads(raw)
        return cart if isinstance(cart, dict) else {}
    except Exception:
        pass
    # Legacy fallback: raw JSON (may arrive double-quoted by the HTTP layer).
    try:
        cart = json.loads(cart_val)
        if isinstance(cart, str):
            cart = json.loads(cart)
        return cart if isinstance(cart, dict) else {}
    except Exception:
        return {}


def parse_cart_key(key: str) -> tuple[str, Optional[str]]:
    """Split a cart key into (product_id, variant_id)."""
    if "::" in key:
        product_id, variant_id = key.split("::", 1)
        return product_id, variant_id or None
    return key, None


async def resolve_cart_items(db: AsyncSession, cart: dict) -> list[dict]:
    """Resolve raw cart keys into displayable line items with variant info."""
    items = []
    for key, qty in cart.items():
        product_id, variant_id = parse_cart_key(key)
        product = await product_service.get_product(db, product_id)
        if not product:
            continue
        variant = None
        if variant_id:
            variant = await variant_service.get_variant(db, variant_id)
        unit_price = product.price
        if variant:
            unit_price = product.price + (variant.price_delta or Decimal("0"))
        subtotal = unit_price * qty
        items.append(
            {
                "key": key,
                "product": product,
                "variant": variant,
                "quantity": qty,
                "unit_price": unit_price,
                "subtotal": subtotal,
            }
        )
    return items


def set_cart_cookie(response: Response, cart: dict, request: Request = None):
    # base64(urlsafe) keeps the cookie value free of quotes/braces, which the
    # HTTP cookie layer (and some clients) would otherwise mangle.
    from app.dependencies import cookie_secure

    encoded = base64.urlsafe_b64encode(json.dumps(cart).encode("utf-8")).decode("ascii")
    response.set_cookie(
        key="cart",
        value=encoded,
        httponly=False,
        max_age=30 * 24 * 60 * 60,
        samesite="lax",  # first-party cart cookie (was 'none', which required Secure)
        path="/",
        secure=cookie_secure(request),
    )


# ==================== PRODUCT DETAIL ====================

@router.get("/products/{product_id}", response_class=HTMLResponse)
async def product_detail(request: Request, product_id: str, db: AsyncSession = Depends(get_db)):
    product = await product_service.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    user = await get_current_user_optional(request, db)
    await user_event_service.record(
        db, "view", user_id=str(user.id) if user else None, product_id=product_id
    )
    categories = await product_service.get_categories(db)
    related = await recommendation_service.get_related(db, product_id)
    variants = await variant_service.list_variants(db, product_id)
    active_variants = [v for v in variants if v.is_active]

    from app.services.review_service import review_service
    reviews = await review_service.get_product_reviews(db, product_id)
    rating = await review_service.get_product_rating(db, product_id)
    reviews_with_author = []
    for r in reviews:
        author = await db.get(User, r.user_id)
        reviews_with_author.append(
            {
                "review": r,
                "author_name": (author.name or author.email) if author else "Cliente",
            }
        )

    return templates.TemplateResponse(
        "products/detail.html",
        {
            "request": request,
            "product": product,
            "categories": categories,
            "related_products": related,
            "variants": active_variants,
            "reviews": reviews_with_author,
            "rating": rating,
            "user": user,
        },
    )


# ==================== CART ====================

@router.get("/cart", response_class=HTMLResponse)
async def cart_page(request: Request, db: AsyncSession = Depends(get_db)):
    cart = get_cart_from_cookie(request)
    items = await resolve_cart_items(db, cart)
    total = sum((item["subtotal"] for item in items), Decimal("0"))
    product_ids = [item["product"].id for item in items]
    cross_sell = await recommendation_service.get_cart_cross_sell(db, product_ids) if product_ids else []
    return templates.TemplateResponse(
        "cart.html",
        {
            "request": request,
            "items": items,
            "total": total,
            "cross_sell": cross_sell,
        },
    )


@router.post("/cart/add/{product_id}")
async def cart_add(
    product_id: str,
    request: Request,
    response: Response,
    variant_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    cart = get_cart_from_cookie(request)
    key = f"{product_id}::{variant_id}" if variant_id else product_id
    cart[key] = cart.get(key, 0) + 1
    set_cart_cookie(response, cart, request)
    user = await get_current_user_optional(request, db)
    await user_event_service.record(
        db, "cart_add", user_id=str(user.id) if user else None, product_id=product_id
    )
    return HTMLResponse(content=str(sum(cart.values())))


@router.get("/cart/add/{product_id}")
async def cart_add_get(
    product_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    variant_id: Optional[str] = None,
):
    """Graceful fallback for no-JS clients and CUA/browser automation."""
    cart = get_cart_from_cookie(request)
    key = f"{product_id}::{variant_id}" if variant_id else product_id
    cart[key] = cart.get(key, 0) + 1
    response = RedirectResponse(url="/cart", status_code=302)
    set_cart_cookie(response, cart, request)
    user = await get_current_user_optional(request, db)
    await user_event_service.record(
        db, "cart_add", user_id=str(user.id) if user else None, product_id=product_id
    )
    return response


@router.post("/cart/remove/{cart_key}")
async def cart_remove(cart_key: str, request: Request, response: Response):
    await validate_csrf(request)
    cart = get_cart_from_cookie(request)
    if cart_key in cart:
        del cart[cart_key]
    set_cart_cookie(response, cart, request)
    return RedirectResponse(url="/cart", status_code=302)


# ==================== CHECKOUT ====================

@router.get("/checkout", response_class=HTMLResponse)
async def checkout_page(request: Request, db: AsyncSession = Depends(get_db)):
    user = await get_current_user_optional(request, db)
    cart = get_cart_from_cookie(request)
    if not cart:
        return RedirectResponse(url="/products/", status_code=302)

    items = await resolve_cart_items(db, cart)
    subtotal = sum((item["subtotal"] for item in items), Decimal("0"))
    total_weight = Decimal("0")
    for item in items:
        product = item["product"]
        weight = product.weight if product.weight else Decimal("0.5")
        total_weight += weight * item["quantity"]

    # Estimate shipping with national zone (real cost calculated on POST with actual address)
    shipping_cost = shipping_service.calculate_shipping_cost(total_weight, "")
    total = subtotal + shipping_cost

    return templates.TemplateResponse(
        "checkout.html",
        {
            "request": request,
            "items": items,
            "subtotal": subtotal,
            "shipping_cost": shipping_cost,
            "total": total,
            "user": user,
            "stripe_key": settings.stripe_publishable_key,
        },
    )


@router.post("/checkout")
async def checkout_create(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    await validate_csrf(request)
    user = await get_current_user_optional(request, db)
    if not user:
        return RedirectResponse(url="/auth/login?next=/checkout", status_code=302)

    form = await request.form()
    cart = get_cart_from_cookie(request)
    if not cart:
        return RedirectResponse(url="/products/", status_code=302)

    # ── Guest checkout: create or reuse a user account ──────────────
    email = (form.get("email") or "").strip().lower()
    if not user:
        if not email:
            return RedirectResponse(url="/checkout?error=email_required", status_code=302)
        from app.services.user_service import user_service
        existing = await user_service.get_user_by_email(db, email)
        if existing:
            user = existing
        else:
            user = await user_service.create_guest_user(db, email, name=form.get("name", "").strip() or None)

    # ── Extract shipping fields ────────────────────────────────────
    name = (form.get("name") or "").strip()
    street = (form.get("street") or "").strip()
    apartment = (form.get("apartment") or "").strip() or None
    city = (form.get("city") or "").strip()
    state = (form.get("state") or "").strip()
    zip_code = (form.get("zip_code") or "").strip()
    country = (form.get("country") or "México").strip()
    phone = (form.get("phone") or "").strip()

    # Server-side validation
    if not all([name, street, city, state, zip_code, phone]):
        return RedirectResponse(url="/checkout", status_code=302)

    # ── Calculate subtotal + weight ─────────────────────────────────
    order_items = []
    subtotal = Decimal("0")
    total_weight = Decimal("0")
    for pid, qty in cart.items():
        product_id, variant_id = parse_cart_key(pid)
        product = await product_service.get_product(db, product_id)
        if product:
            order_items.append(
                OrderItemCreate(
                    product_id=product_id,
                    quantity=qty,
                    variant_id=variant_id,
                )
            )
            unit_price = product.price
            if variant_id:
                variant = await variant_service.get_variant(db, variant_id)
                if variant:
                    unit_price = product.price + (variant.price_delta or Decimal("0"))
            subtotal += unit_price * qty
            weight = product.weight if product.weight else Decimal("0.5")
            total_weight += weight * qty

    if not order_items:
        return RedirectResponse(url="/products/", status_code=302)

    # ── Calculate shipping cost ─────────────────────────────────────
    shipping_cost = shipping_service.calculate_shipping_cost(
        total_weight, state, destination_country=country
    )

    # ── Persist shipping address ────────────────────────────────────
    address_data = ShippingAddressCreate(
        name=name,
        phone=phone,
        street=street,
        apartment=apartment,
        city=city,
        state=state,
        zip_code=zip_code,
        country=country,
    )
    await shipping_service.create_address(db, user.id, address_data)

    # ── Create order with shipping ──────────────────────────────────
    shipping_address_dict = {
        "name": name,
        "street": street,
        "apartment": apartment,
        "city": city,
        "state": state,
        "zip_code": zip_code,
        "country": country,
        "phone": phone,
    }
    order_data = OrderCreate(
        items=order_items,
        shipping_address=shipping_address_dict,
        customer_rfc=(form.get("customer_rfc") or "").strip() or None,
        uso_cfdi=(form.get("uso_cfdi") or "G03").strip() or None,
    )
    order = await order_service.create_order(db, user.id, order_data)

    # Apply shipping cost to order
    order.shipping_amount = shipping_cost
    order.total_amount = subtotal + shipping_cost

    await db.commit()

    # ── Clear cart ──────────────────────────────────────────────────
    response.delete_cookie("cart")

    # ── Stripe checkout session ─────────────────────────────────────
    success_url = f"{settings.frontend_url}/checkout/success?order_id={order.id}&payment=stripe"
    cancel_url = f"{settings.frontend_url}/checkout/cancel"
    stripe_result = await stripe_service.create_checkout_session(order, success_url, cancel_url)

    return RedirectResponse(url=stripe_result["url"], status_code=302)


@router.get("/checkout/success", response_class=HTMLResponse)
async def checkout_success(request: Request, order_id: str):
    return templates.TemplateResponse("checkout_success.html", {"request": request, "order_id": order_id})


@router.get("/checkout/cancel", response_class=HTMLResponse)
async def checkout_cancel(request: Request):
    return templates.TemplateResponse("checkout_cancel.html", {"request": request})


# ==================== ACCOUNT ====================

@router.get("/account", response_class=HTMLResponse)
async def account_page(request: Request, db: AsyncSession = Depends(get_db)):
    user = await get_current_user_optional(request, db)
    if not user:
        return RedirectResponse(url="/auth/login?next=/account", status_code=302)
    orders = await order_service.get_user_orders(db, user.id)
    return templates.TemplateResponse(
        "account.html",
        {"request": request, "user": user, "orders": orders},
    )


# ==================== SEARCH ====================

@router.get("/search", response_class=HTMLResponse)
async def search_page(
    request: Request,
    q: str = "",
    db: AsyncSession = Depends(get_db),
):
    products = []
    ai_expanded = False
    expanded_terms = []
    if q:
        result = await search_service.search_with_expansion(db, query=q)
        products = result.get("products", [])
        ai_expanded = result.get("ai_expanded", False)
        expanded_terms = result.get("expanded_terms", [])
    return templates.TemplateResponse(
        "search.html",
        {
            "request": request,
            "products": products,
            "q": q,
            "ai_expanded": ai_expanded,
            "expanded_terms": expanded_terms,
        },
    )


# ==================== ADMIN ====================

@router.get("/admin/promotions", response_class=HTMLResponse)
async def admin_promotions_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    result = await db.execute(select(Promotion).order_by(Promotion.created_at.desc()))
    promotions = result.scalars().all()
    return templates.TemplateResponse(
        "admin/promotions.html",
        {"request": request, "promotions": promotions, "user": user},
    )
