from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from app.config import settings
from app.database import init_db, get_db
from app.middleware import rate_limit_middleware, SecurityHeadersMiddleware, setup_cors, CSRFMiddleware, CanonicalDomainMiddleware
from app.services.product_service import product_service
from app.services.recommendation_service import recommendation_service
from app.services.personalization_service import personalization_service
from app.dependencies import get_current_user_optional
from app.routers import (
    auth_router,
    products_router,
    admin_products_router,
    admin_photos_router,
    orders_router,
    payments_router,
    loyalty_router,
    promotions_router,
    admin_promotions_router,
    admin_dashboard_router,
    reviews_router,
    wishlist_router,
    search_router,
    voice_router,
    shipping_router,
    refunds_router,
)
from app.routers.admin_rag import router as admin_rag_router
from app.routers.admin_analytics import router as admin_analytics_router
from app.routers.admin_pricing import router as admin_pricing_router
from app.routers.admin_cart_recovery import router as admin_cart_recovery_router
from app.routers.admin_shipments import router as admin_shipments_router
from app.routers.admin_reports import router as admin_reports_router
from app.routers.admin_variants import router as admin_variants_router
from app.routers.admin_search import router as admin_search_router
from app.routers.pages import router as pages_router
from app.routers.chat import router as chat_router
from app.routers.legal import router as legal_router
from app.routers.support import router as support_router
from app.routers.admin_support import router as admin_support_router
from app.routers.admin_invoices import router as admin_invoices_router
from app.routers.admin_email_queue import router as admin_email_queue_router
from app.routers.invoice_validation import router as invoice_validation_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
    version="1.0.0",
    lifespan=lifespan,
)

# Canonical domain redirect (e.g. www -> non-www) when ALLOWED_HOSTS is set.
if settings.allowed_hosts_list != ["*"]:
    app.add_middleware(CanonicalDomainMiddleware)

# Production hardening: force HTTPS and validate hosts before custom domain setup.
if settings.force_https:
    app.add_middleware(HTTPSRedirectMiddleware)

if settings.allowed_hosts_list != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts_list)

# Static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
from app.templates_instance import templates

# Setup CORS
setup_cors(app)

# Add CSRF token cookie to every response
app.add_middleware(CSRFMiddleware)

# Add security headers
app.add_middleware(SecurityHeadersMiddleware)

# Add rate limiting
app.middleware("http")(rate_limit_middleware)

# Register routers
app.include_router(pages_router)
app.include_router(chat_router)
app.include_router(legal_router)
app.include_router(support_router)
app.include_router(admin_support_router)
app.include_router(admin_invoices_router)
app.include_router(admin_email_queue_router)
app.include_router(invoice_validation_router)
app.include_router(auth_router)
app.include_router(products_router)
app.include_router(admin_products_router)
app.include_router(admin_photos_router)
app.include_router(orders_router)
app.include_router(payments_router)
app.include_router(loyalty_router)
app.include_router(promotions_router)
app.include_router(admin_promotions_router)
app.include_router(admin_dashboard_router)
app.include_router(admin_rag_router)
app.include_router(admin_analytics_router)
app.include_router(admin_pricing_router)
app.include_router(admin_cart_recovery_router)
app.include_router(admin_shipments_router)
app.include_router(admin_reports_router)
app.include_router(admin_variants_router)
app.include_router(admin_search_router)
app.include_router(reviews_router)
app.include_router(wishlist_router)
app.include_router(search_router)
app.include_router(voice_router)
app.include_router(shipping_router)
app.include_router(refunds_router)


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    db_ok = False
    try:
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    
    status_code = 200 if db_ok else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ok" if db_ok else "degraded",
            "database": "connected" if db_ok else "disconnected",
            "app": settings.app_name,
            "version": "1.0.0",
            "environment": "production" if not settings.debug else "development",
        },
    )


@app.get("/", response_class=HTMLResponse)
async def root(request: Request, db: AsyncSession = Depends(get_db)):
    """Homepage"""
    user = await get_current_user_optional(request, db)
    products = await product_service.get_products(db, None)
    featured = products[:3] if products else []
    trending = await recommendation_service.get_trending(db)
    personalized = await personalization_service.recommend_for_user(
        db, str(user.id) if user else None, n=8
    )
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "featured_products": featured,
            "trending_products": trending,
            "personalized_products": personalized["products"],
            "personalized_reason": personalized.get("reason"),
            "personalized": personalized["personalized"],
            "user": user,
        },
    )


@app.get("/products", response_class=HTMLResponse)
async def products_redirect():
    return RedirectResponse(url="/products/")


@app.get("/products/", response_class=HTMLResponse)
async def products_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Products listing page"""
    user = await get_current_user_optional(request, db)
    products = await product_service.get_products(db, None)
    categories = await product_service.get_categories(db)
    return templates.TemplateResponse(
        "products/list.html",
        {"request": request, "products": products, "categories": categories, "user": user},
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=404,
            content={"detail": "Not found"}
        )
    return JSONResponse(
        status_code=404,
        content={"detail": "Page not found"}
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
