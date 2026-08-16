from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_admin
from app.models.user import User
from app.services.semantic_search_service import semantic_search_service
from app.templates_instance import templates


router = APIRouter(prefix="/admin/search", tags=["admin-search"])


@router.get("/")
async def admin_search_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    facets = await semantic_search_service.get_facet_values(db)
    return templates.TemplateResponse(
        "admin/search.html",
        {
            "request": request,
            "enabled": semantic_search_service.enabled,
            "facets": facets,
        },
    )


@router.post("/reindex")
async def reindex_search(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    count = await semantic_search_service.index_products(db)
    return JSONResponse({"status": "ok", "indexed_products": count})


@router.get("/stats")
async def search_stats(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    facets = await semantic_search_service.get_facet_values(db)
    return JSONResponse(
        {
            "enabled": semantic_search_service.enabled,
            "source": "meilisearch" if semantic_search_service.enabled else "sql",
            "facets": facets,
        }
    )
