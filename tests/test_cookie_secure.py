"""Lock the cookie Secure-flag behavior.

The storefront broke when cookies were marked Secure from FRONTEND_URL (https)
during local HTTP dev. The flag must come from FORCE_HTTPS, the real request
scheme, or a TLS-terminating proxy's X-Forwarded-Proto header — never from
FRONTEND_URL.
"""
import pytest
from starlette.requests import Request

from app.dependencies import cookie_secure


def _req(scheme="http", xfp=None):
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "scheme": scheme,
        "headers": [],
        "query_string": b"",
        "server": ("test", 80),
        "client": ("127.0.0.1", 12345),
    }
    if xfp:
        scope["headers"].append((b"x-forwarded-proto", xfp.encode()))
    return Request(scope)


def test_force_https_wins(monkeypatch):
    import app.dependencies as mod

    monkeypatch.setattr(mod.settings, "force_https", True)
    assert cookie_secure(_req(scheme="http")) is True


def test_https_scheme(monkeypatch):
    import app.dependencies as mod

    monkeypatch.setattr(mod.settings, "force_https", False)
    assert cookie_secure(_req(scheme="https")) is True


def test_local_http_is_not_secure(monkeypatch):
    import app.dependencies as mod

    monkeypatch.setattr(mod.settings, "force_https", False)
    assert cookie_secure(_req(scheme="http")) is False


def test_proxy_forwarded_https(monkeypatch):
    import app.dependencies as mod

    monkeypatch.setattr(mod.settings, "force_https", False)
    assert cookie_secure(_req(scheme="http", xfp="https")) is True


def test_proxy_forwarded_http(monkeypatch):
    import app.dependencies as mod

    monkeypatch.setattr(mod.settings, "force_https", False)
    assert cookie_secure(_req(scheme="http", xfp="http")) is False


@pytest.mark.asyncio
async def test_auth_cookie_secure_flag_over_local_http(client, db, monkeypatch):
    """POST /auth/login/web over http:// must NOT set Secure, or the browser
    won't send the session cookie back and login appears broken."""
    import app.dependencies as mod

    monkeypatch.setattr(mod.settings, "force_https", False)

    from app.models.user import User
    from app.services.auth_service import get_password_hash, create_access_token

    user = User(
        email="cookie.secure@test.com",
        hashed_password=get_password_hash("pass12345"),
        name="Cookie",
    )
    db.add(user)
    await db.commit()

    # Prime the CSRF cookie (set by middleware on any GET response).
    await client.get("/")
    csrf = client.cookies.get("csrf_token", "")

    resp = await client.post(
        "/auth/login/web",
        json={"email": "cookie.secure@test.com", "password": "pass12345"},
        headers={"X-CSRF-Token": csrf},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    set_cookie = resp.headers.get("set-cookie", "")
    assert "access_token" in set_cookie
    assert "Secure" not in set_cookie  # http dev must not get a Secure cookie
