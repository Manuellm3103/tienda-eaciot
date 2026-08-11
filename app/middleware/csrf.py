"""CSRF protection helpers.

Strategy:
- A token is generated on first request and stored in a cookie.
- Forms include the token as a hidden field.
- State-changing routes validate the cookie token against the form field.
"""
import secrets
from fastapi import Request, HTTPException
from starlette.responses import Response

CSRF_COOKIE_NAME = "csrf_token"
CSRF_FORM_FIELD = "_csrf_token"


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def get_csrf_token(request: Request) -> str:
    """Return existing CSRF token from cookie or generate a new one."""
    return request.cookies.get(CSRF_COOKIE_NAME) or generate_csrf_token()


def set_csrf_cookie(response: Response, token: str, secure: bool = False):
    """Set the CSRF token cookie on a response."""
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        httponly=False,
        max_age=30 * 24 * 60 * 60,
        samesite="lax",
        secure=secure,
    )


async def validate_csrf(request: Request):
    """Validate that the form or header CSRF token matches the cookie."""
    if request.method == "GET":
        return
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    if not cookie_token:
        raise HTTPException(status_code=403, detail="CSRF cookie missing")

    # Check form field first, then HTMX header, then JSON body.
    form_token = None
    header_token = request.headers.get("X-CSRF-Token")
    if header_token:
        form_token = header_token
    else:
        try:
            form = await request.form()
            form_token = form.get(CSRF_FORM_FIELD)
        except Exception:
            form_token = None
        if not form_token:
            try:
                body = await request.json()
                form_token = body.get(CSRF_FORM_FIELD) if isinstance(body, dict) else None
            except Exception:
                form_token = None

    if not form_token or cookie_token != form_token:
        raise HTTPException(status_code=403, detail="CSRF token missing or invalid")
