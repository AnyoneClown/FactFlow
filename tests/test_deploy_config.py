from pathlib import Path

from config.settings import prod


def test_production_settings_use_secure_static_and_https_defaults():
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


def test_readme_documents_local_and_render_deploy():
    readme = Path("README.md").read_text()

    assert "## Local run" in readme
    assert "## Render deploy" in readme
    assert "Supabase PostgreSQL" in readme
    assert "gunicorn config.wsgi:application" in readme


def test_render_yaml_defines_docker_web_service():
    render_yaml = Path("render.yaml").read_text()

    assert "type: web" in render_yaml
    assert "runtime: docker" in render_yaml
    assert "healthCheckPath: /health" in render_yaml
    assert "DJANGO_SETTINGS_MODULE" in render_yaml
    assert "config.settings.prod" in render_yaml
    assert "DATABASE_URL" in render_yaml
