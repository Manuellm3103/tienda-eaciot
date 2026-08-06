from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.config import settings
from app.database import init_db
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


app = FastAPI(title=settings.app_name)

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
    return {"status": "ok", "app": settings.app_name}
