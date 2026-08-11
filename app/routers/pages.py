import json
import uuid
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.models.product import Product, Category
from app.models.order import Order
from app.models.promotion import Promotion
from app.schemas.order import OrderCreate, OrderItemCreate
from app.services.auth_service import decode_token
from app.services.product_service import product_service
from app.services.order_service import order_service
from app.services.promotion_service import promotion_service
from app.services.stripe_service import stripe_service
from app.services.search_service import search_service
from app.middleware import validate_csrf
from app.config import settings

router = APIRouter(tags=["pages"])
from app.templates_instance import templates


def get_cart_from_cookie(request: Request) -> dict:
    cart_json = request.cookies.get("cart", "{}")
    try:
        return json.loads(cart_json)
    except Exception:
        return {}


def set_cart_cookie(response: Response, cart: dict):
    response.set_cookie(
        key="cart",
        value=json.dumps(cart),
        httponly=False,
        max_age=30 * 24 * 60 * 60,
        samesite="lax",
    )


async def get_current_user_optional(request: Request, db: AsyncSession = Depends(get_db)) -> Optional[User]:
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = decode_token(token)
    if not payload or not payload.get("sub"):
        return None
    result = await db.execute(select(User).where(User.id == payload["sub"]))
    return result.scalar_one_or_none()


# ==================== PRODUCT DETAIL ====================

@router.get("/products/{product_id}", response_class=HTMLResponse)
async def product_detail(request: Request, product_id: str, db: AsyncSession = Depends(get_db)):
    product = await product_service.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    categories = await product_service.get_categories(db)
    return templates.TemplateResponse(
        "products/detail.html",
        {"request": request, "product": product, "categories": categories},
    )


# ==================== CART ====================

@router.get("/cart", response_class=HTMLResponse)
async def cart_page(request: Request, db: AsyncSession = Depends(get_db)):
    cart = get_cart_from_cookie(request)
    items = []
    total = Decimal("0")
    for pid, qty in cart.items():
        product = await product_service.get_product(db, pid)
        if product:
            subtotal = product.price * qty
            items.append({"product": product, "quantity": qty, "subtotal": subtotal})
            total += subtotal
    return templates.TemplateResponse(
        "cart.html",
        {"request": request, "items": items, "total": total},
    )


@router.post("/cart/add/{product_id}")
async def cart_add(product_id: str, request: Request, response: Response):
    cart = get_cart_from_cookie(request)
    cart[product_id] = cart.get(product_id, 0) + 1
    set_cart_cookie(response, cart)
    return HTMLResponse(content=str(sum(cart.values())))


@router.get("/cart/add/{product_id}")
async def cart_add_get(product_id: str, request: Request):
    """Graceful fallback for no-JS clients and CUA/browser automation."""
    cart = get_cart_from_cookie(request)
    cart[product_id] = cart.get(product_id, 0) + 1
    response = RedirectResponse(url="/cart", status_code=302)
    set_cart_cookie(response, cart)
    return response


@router.post("/cart/remove/{product_id}")
async def cart_remove(product_id: str, request: Request, response: Response):
    await validate_csrf(request)
    cart = get_cart_from_cookie(request)
    if product_id in cart:
        del cart[product_id]
    set_cart_cookie(response, cart)
    return RedirectResponse(url="/cart", status_code=302)


# ==================== CHECKOUT ====================

@router.get("/checkout", response_class=HTMLResponse)
async def checkout_page(request: Request, db: AsyncSession = Depends(get_db)):
    user = await get_current_user_optional(request, db)
    if not user:
        return RedirectResponse(url="/auth/login?next=/checkout", status_code=302)
    cart = get_cart_from_cookie(request)
    if not cart:
        return RedirectResponse(url="/products/", status_code=302)
    items = []
    total = Decimal("0")
    for pid, qty in cart.items():
        product = await product_service.get_product(db, pid)
        if product:
            subtotal = product.price * qty
            items.append({"product": product, "quantity": qty, "subtotal": subtotal})
            total += subtotal
    return templates.TemplateResponse(
        "checkout.html",
        {"request": request, "items": items, "total": total, "user": user, "stripe_key": settings.stripe_publishable_key},
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
    
    items = [OrderItemCreate(product_id=pid, quantity=qty) for pid, qty in cart.items()]
    shipping_address = {
        "name": form.get("name", ""),
        "email": form.get("email", ""),
        "address": form.get("address", ""),
        "city": form.get("city", ""),
        "country": form.get("country", ""),
        "postal_code": form.get("postal_code", ""),
    }
    
    order_data = OrderCreate(items=items, shipping_address=shipping_address)
    order = await order_service.create_order(db, user.id, order_data)
    await db.commit()
    
    # Clear cart
    response.delete_cookie("cart")
    
    # Create Stripe checkout session
    success_url = f"{settings.frontend_url}/checkout/success?order_id={order.id}&payment=stripe"
    cancel_url = f"{settings.frontend_url}/checkout/cancel"
    stripe_result = await stripe_service.create_checkout_session(order, success_url, cancel_url)
    
    # Redirect to Stripe
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
    if q:
        result = await search_service.search_products(db, query=q)
        products = result.get("products", [])
    return templates.TemplateResponse(
        "search.html",
        {"request": request, "products": products, "q": q},
    )


# ==================== ADMIN ====================

@router.get("/admin/promotions", response_class=HTMLResponse)
async def admin_promotions_page(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Promotion).order_by(Promotion.created_at.desc()))
    promotions = result.scalars().all()
    return templates.TemplateResponse(
        "admin/promotions.html",
        {"request": request, "promotions": promotions},
    )
