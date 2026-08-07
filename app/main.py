from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from app.config import settings
from app.database import init_db
from app.middleware import rate_limit_middleware, SecurityHeadersMiddleware, setup_cors
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
)


app = FastAPI(
    title=settings.app_name,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
)

# Setup CORS
setup_cors(app)

# Add security headers
app.add_middleware(SecurityHeadersMiddleware)

# Add rate limiting
app.middleware("http")(rate_limit_middleware)

# Register routers
app.include_router(auth_router)
app.include_router(products_router)
app.include_router(admin_products_router)
app.include_router(orders_router)
app.include_router(payments_router)
app.include_router(loyalty_router)
app.include_router(promotions_router)
app.include_router(admin_promotions_router)
app.include_router(admin_dashboard_router)


@app.on_event("startup")
async def startup():
    await init_db()


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": "1.0.0",
        "environment": "production" if not settings.debug else "development",
    }


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=404,
            content={"detail": "Not found"}
        )
    # For web routes, you could return a custom 404 page
    return JSONResponse(
        status_code=404,
        content={"detail": "Page not found"}
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    # Log the error (would integrate with Sentry in production)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
