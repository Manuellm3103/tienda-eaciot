from app.routers.auth import router as auth_router
from app.routers.products import router as products_router
from app.routers.admin_products import router as admin_products_router
from app.routers.orders import router as orders_router
from app.routers.payments import router as payments_router
from app.routers.loyalty import router as loyalty_router
from app.routers.promotions import router as promotions_router
from app.routers.admin_promotions import router as admin_promotions_router
from app.routers.admin_dashboard import router as admin_dashboard_router

__all__ = [
    "auth_router",
    "products_router",
    "admin_products_router",
    "orders_router",
    "payments_router",
    "loyalty_router",
    "promotions_router",
    "admin_promotions_router",
    "admin_dashboard_router",
]
