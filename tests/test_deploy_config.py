import importlib
import sys
from pathlib import Path


def load_prod_settings(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("ALLOWED_HOSTS", "factflow.example.com")
    monkeypatch.setenv("CSRF_TRUSTED_ORIGINS", "https://factflow.example.com")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///tmp/factflow-prod-test.sqlite3")
    sys.modules.pop("config.settings.prod", None)

    from config.settings import prod

    return importlib.reload(prod)


def test_production_settings_use_secure_static_and_https_defaults(monkeypatch):
    prod = load_prod_settings(monkeypatch)

    assert prod.DEBUG is False
    assert prod.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")
    assert prod.SECURE_SSL_REDIRECT is True
    assert prod.SESSION_COOKIE_SECURE is True
    assert prod.CSRF_COOKIE_SECURE is True
    assert prod.STORAGES["staticfiles"]["BACKEND"] == (
        "whitenoise.storage.CompressedManifestStaticFilesStorage"
    )


def test_build_script_contains_collectstatic_command():
    build_script = Path("build.sh").read_text()

    assert "poetry install" in build_script
    assert "collectstatic --noinput" in build_script
