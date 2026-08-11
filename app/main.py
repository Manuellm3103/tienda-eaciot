from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from app.config import settings
from app.database import init_db, get_db
from app.middleware import rate_limit_middleware, SecurityHeadersMiddleware, setup_cors, CSRFMiddleware
from app.services.product_service import product_service
from app.routers import (
    auth_router,
    products_router,
    admin_products_router,
    orders_router,
    payments_router,
    loyalty_router,
    promotions_router,
    admin_promotions_router,
    admin_dashboard_router,
    reviews_router,
    wishlist_router,
    search_router,
    shipping_router,
    refunds_router,
)
from app.routers.pages import router as pages_router


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
app.include_router(auth_router)
app.include_router(products_router)
app.include_router(admin_products_router)
app.include_router(orders_router)
app.include_router(payments_router)
app.include_router(loyalty_router)
app.include_router(promotions_router)
app.include_router(admin_promotions_router)
app.include_router(admin_dashboard_router)
app.include_router(reviews_router)
app.include_router(wishlist_router)
app.include_router(search_router)
app.include_router(shipping_router)
app.include_router(refunds_router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": "1.0.0",
        "environment": "production" if not settings.debug else "development",
    }


@app.get("/", response_class=HTMLResponse)
async def root(request: Request, db: AsyncSession = Depends(get_db)):
    """Homepage"""
    products = await product_service.get_products(db, None)
    featured = products[:3] if products else []
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "featured_products": featured},
    )


@app.get("/products", response_class=HTMLResponse)
async def products_redirect():
    return RedirectResponse(url="/products/")


@app.get("/products/", response_class=HTMLResponse)
async def products_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Products listing page"""
    products = await product_service.get_products(db, None)
    categories = await product_service.get_categories(db)
    return templates.TemplateResponse(
        "products/list.html",
        {"request": request, "products": products, "categories": categories},
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
