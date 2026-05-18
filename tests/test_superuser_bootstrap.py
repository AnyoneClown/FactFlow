import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.imports.models import ImportedFact, UploadLog


@pytest.mark.django_db
def test_bootstrap_local_creates_superuser_from_env(settings):
    settings.DJANGO_SUPERUSER_EMAIL = "local-admin@example.com"
    settings.DJANGO_SUPERUSER_PASSWORD = "localpass123"

    call_command("bootstrap_local", verbosity=0)

    user = get_user_model().objects.get(email="local-admin@example.com")
    assert user.is_superuser is True
    assert user.is_staff is True
    assert user.check_password("localpass123") is True


@pytest.mark.django_db
def test_bootstrap_local_loads_demo_data_once_and_keeps_superuser(settings):
    settings.DJANGO_SUPERUSER_EMAIL = "local-admin@example.com"
    settings.DJANGO_SUPERUSER_PASSWORD = "localpass123"

    call_command("bootstrap_local", verbosity=0)
    call_command("bootstrap_local", verbosity=0)

    assert get_user_model().objects.filter(email="local-admin@example.com").count() == 1
    assert get_user_model().objects.filter(email="admin@factflow.local").count() == 1
    assert UploadLog.objects.count() == 4
    assert ImportedFact.objects.count() == 8


def test_docker_compose_sets_default_superuser_env():
    compose_text = open("docker-compose.yml", encoding="utf-8").read()

    assert "DJANGO_SUPERUSER_EMAIL=${DJANGO_SUPERUSER_EMAIL:-admin@example.com}" in compose_text
    assert "DJANGO_SUPERUSER_PASSWORD=${DJANGO_SUPERUSER_PASSWORD:-admin12345}" in compose_text
