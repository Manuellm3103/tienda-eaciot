from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.templates_instance import templates

router = APIRouter(tags=["legal"])


@router.get("/terminos", response_class=HTMLResponse)
async def terms(request: Request):
    return templates.TemplateResponse("legal/terms.html", {"request": request})


@router.get("/privacidad", response_class=HTMLResponse)
async def privacy(request: Request):
    return templates.TemplateResponse("legal/privacy.html", {"request": request})


@router.get("/cookies", response_class=HTMLResponse)
async def cookies(request: Request):
    return templates.TemplateResponse("legal/cookies.html", {"request": request})
