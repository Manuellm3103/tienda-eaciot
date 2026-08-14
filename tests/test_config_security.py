import pytest
from app.config import Settings


def test_production_requires_real_secret_key():
    """With force_https (production) and default secret, config must refuse."""
    with pytest.raises(ValueError, match="APP_SECRET_KEY"):
        Settings(
            force_https=True,
            app_secret_key="change-me",
            _env_file=None,
        )


def test_production_accepts_real_secret_key():
    s = Settings(
        force_https=True,
        app_secret_key="a-strong-random-secret-value-123",
        _env_file=None,
    )
    assert s.app_secret_key == "a-strong-random-secret-value-123"


def test_dev_allows_default_secret():
    """Local dev (force_https off) keeps working with the placeholder."""
    s = Settings(force_https=False, app_secret_key="change-me", _env_file=None)
    assert s.app_secret_key == "change-me"
