from app.routers.auth import router as auth_router
from app.routers.products import router as products_router
from app.routers.admin_products import router as admin_products_router
from app.routers.orders import router as orders_router
from app.routers.payments import router as payments_router
from app.routers.loyalty import router as loyalty_router
from app.routers.promotions import router as promotions_router
from app.routers.admin_promotions import router as admin_promotions_router
from app.routers.admin_dashboard import router as admin_dashboard_router
from app.routers.reviews import router as reviews_router
from app.routers.wishlist import router as wishlist_router
from app.routers.search import router as search_router
from app.routers.voice import router as voice_router
from app.routers.shipping import router as shipping_router
from app.routers.refunds import router as refunds_router

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
    "reviews_router",
    "wishlist_router",
    "search_router",
    "voice_router",
    "shipping_router",
    "refunds_router",
]
