from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_admin
from app.models.user import User
from app.services.visual_search import visual_search_service


router = APIRouter(prefix="/api/visual-search", tags=["visual-search"])


@router.post("/")
async def visual_search(
    image: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload an image and find visually similar products."""
    if not visual_search_service.enabled:
        raise HTTPException(status_code=503, detail="Visual search no está disponible")
    contents = await image.read()
    results = await visual_search_service.search(db, contents, top_k=10)
    return JSONResponse({"results": results})


@router.post("/admin/index-all")
async def index_all_images(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Admin endpoint to re-index all product images."""
    count = await visual_search_service.index_all_products(db)
    return JSONResponse({"status": "ok", "indexed_products": count})
