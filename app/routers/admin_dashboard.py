import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.dashboard_service import dashboard_service
from app.dependencies import require_admin
from app.templates_instance import templates

router = APIRouter(
    prefix="/admin",
    tags=["admin-dashboard"],
    dependencies=[Depends(require_admin)],
)

# Cada cuántos segundos el dashboard en vivo (SSE) re-emite el estado.
LIVE_INTERVAL_SECONDS = 10


def _render_live_html(request: Request, metrics: dict) -> str:
    """Renderiza el partial de métricas en vivo a HTML (para SSE y polling)."""
    tpl = templates.env.get_template("admin/_live.html")
    return tpl.render(request=request, metrics=metrics)


@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard_page(request: Request, db: AsyncSession = Depends(get_db)):
    metrics = await dashboard_service.get_dashboard_metrics(db)
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {"request": request, "metrics": metrics},
    )


@router.get("/dashboard/partial", response_class=HTMLResponse)
async def dashboard_partial(request: Request, db: AsyncSession = Depends(get_db)):
    """Partial HTML de métricas en vivo. Usado como fallback si el proxy
    bufferiza el SSE (polling cada N segundos desde el navegador)."""
    metrics = await dashboard_service.get_dashboard_metrics(db)
    return HTMLResponse(_render_live_html(request, metrics))


async def _dashboard_events(request: Request, db: AsyncSession):
    """Generador SSE: emite un evento 'metrics' con el partial en vivo cada
    LIVE_INTERVAL_SECONDS.

    La desconexión del cliente se detecta al cancelar el generador en el
    siguiente yield/sleep (no confiar en request.is_disconnected(), que en
    algunos transports marca el canal como desconectado de inmediato).
    """
    while True:
        try:
            metrics = await dashboard_service.get_dashboard_metrics(db)
            html = _render_live_html(request, metrics)
            payload = json.dumps({"html": html}, ensure_ascii=False)
            yield f"event: metrics\ndata: {payload}\n\n"
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            # Nunca tumbar el stream: envía el error como evento y sigue.
            yield f"event: error\ndata: {json.dumps({'detail': str(exc)[:200]}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(LIVE_INTERVAL_SECONDS)


@router.get("/dashboard/live")
async def dashboard_live_sse(request: Request, db: AsyncSession = Depends(get_db)):
    """Server-Sent Events: empuja las métricas del dashboard en tiempo real.

    Innovación sobre el patrón clásico de polling: un solo GET que mantiene el
    canal abierto y re-emite el estado cada LIVE_INTERVAL_SECONDS. EventSource
    del navegador se reconecta solo si se cae la conexión. Si el proxy de la
    plataforma bufferiza, el frontend cae a /dashboard/partial (polling).
    """
    return StreamingResponse(
        _dashboard_events(request, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/dashboard/data")
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    return await dashboard_service.get_dashboard_metrics(db)


@router.get("/ai/suggestions")
async def get_ai_suggestions(db: AsyncSession = Depends(get_db)):
    return await dashboard_service.get_ai_suggestions(db)


@router.get("/ai/suggestions/partial", response_class=HTMLResponse)
async def ai_suggestions_partial(request: Request, db: AsyncSession = Depends(get_db)):
    """Partial HTMX para el panel de sugerencias IA.

    Antes el template apuntaba a esta ruta pero no existía → el panel se quedaba
    en 'Cargando...' para siempre. Ahora renderiza el partial con estado de
    error/empty para no dejar al admin colgado cuando la IA no responde."""
    try:
        suggestions = await asyncio.wait_for(
            dashboard_service.get_ai_suggestions(db), timeout=8
        )
        return templates.TemplateResponse(
            "admin/_ai_suggestions.html",
            {"request": request, "suggestions": suggestions, "error": None},
        )
    except Exception as exc:  # noqa: BLE001
        return templates.TemplateResponse(
            "admin/_ai_suggestions.html",
            {"request": request, "suggestions": None, "error": str(exc)},
        )


@router.post("/ai/suggestions/approve")
async def approve_suggestion(
    suggestion_type: str,
    suggestion_data: dict,
    db: AsyncSession = Depends(get_db)
):
    return await dashboard_service.approve_suggestion(db, suggestion_type, suggestion_data)
