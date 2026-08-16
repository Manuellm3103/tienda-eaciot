"""Admin routes for AI product photo enhancement (#14 on the innovation roadmap)."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import require_admin
from app.middleware import validate_csrf
from app.services.product_service import product_service
from app.services.image_enhance_service import image_enhance_service
import httpx
import io

router = APIRouter(
    prefix="/admin/products",
    tags=["admin-photos"],
    dependencies=[Depends(require_admin)],
)


async def _fetch_image(image_url: str) -> bytes:
    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        resp = await client.get(image_url)
    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Could not download image")
    return resp.content


@router.post("/{product_id}/enhance-photo")
async def admin_enhance_photo(
    request: Request,
    product_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Return an AI-enhanced PNG of the product's image_url."""
    await validate_csrf(request)
    product = await product_service.get_product(db, product_id)
    if not product or not product.image_url:
        raise HTTPException(status_code=404, detail="Product or image not found")

    try:
        image_bytes = await _fetch_image(product.image_url)
        enhanced = image_enhance_service.enhance_product_photo(image_bytes)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Enhancement failed: {exc}") from exc

    return StreamingResponse(
        io.BytesIO(enhanced),
        media_type="image/png",
        headers={
            "Content-Disposition": f'attachment; filename="{product_id}_enhanced.png"'
        },
    )


@router.post("/{product_id}/social-square")
async def admin_social_square(
    request: Request,
    product_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Return a 1080x1080 social-media square of the product's image_url."""
    await validate_csrf(request)
    product = await product_service.get_product(db, product_id)
    if not product or not product.image_url:
        raise HTTPException(status_code=404, detail="Product or image not found")

    try:
        image_bytes = await _fetch_image(product.image_url)
        square = image_enhance_service.generate_social_media_square(
            image_bytes, text=product.title
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Square generation failed: {exc}") from exc

    return StreamingResponse(
        io.BytesIO(square),
        media_type="image/png",
        headers={
            "Content-Disposition": f'attachment; filename="{product_id}_social.png"'
        },
    )
