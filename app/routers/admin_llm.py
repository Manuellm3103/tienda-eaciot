from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import get_db
from app.dependencies import require_admin
from app.middleware import validate_csrf
from app.services.app_setting_service import get_setting, set_setting
from app.ai.llm_router import llm_router

router = APIRouter(
    prefix="/admin/llm",
    tags=["admin-llm"],
    dependencies=[Depends(require_admin)],
)

ALLOWED_PROVIDERS = {"ollama", "opencode"}


@router.get("/models")
async def list_models(db: AsyncSession = Depends(get_db)):
    """Modelos disponibles + selección actual + diagnóstico de configuración.

    No expone secretos: solo booleans de si la key está seteada y los hosts
    (que ya son públicos en .env / no son secretos).
    """
    models = await llm_router.list_models()
    provider = (await get_setting(db, "llm_provider", "")).strip()
    model = (await get_setting(db, "llm_model", "")).strip()
    return JSONResponse({
        "models": models,
        "current": {"provider": provider, "model": model},
        "config": {
            "ollama_host": settings.ollama_host,
            "ollama_default_model": settings.ollama_model,
            "ollama_api_key_set": bool(settings.ollama_api_key),
            "opencode_host": settings.opencode_host,
            "opencode_default_model": settings.opencode_model,
            "opencode_api_key_set": bool(settings.opencode_api_key),
        },
    })


@router.post("/model")
async def set_model(
    request: Request,
    db: AsyncSession = Depends(get_db),
    provider: str = Form(""),
    model: str = Form(""),
):
    """Persiste el modelo elegido por el admin para el depto de marketing IA.

    provider='' o model='' limpia la selección y vuelve a la ruta automática.
    """
    await validate_csrf(request)
    provider = provider.strip().lower()
    model = model.strip()

    if provider and provider not in ALLOWED_PROVIDERS:
        raise HTTPException(status_code=400, detail="Proveedor no válido")

    await set_setting(db, "llm_provider", provider)
    await set_setting(db, "llm_model", model)
    await db.commit()
    return JSONResponse({"ok": True, "provider": provider, "model": model})
