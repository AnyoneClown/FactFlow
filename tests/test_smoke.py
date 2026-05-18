from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.urls import reverse
from pathlib import Path


def test_django_system_check_passes():
    call_command("check")


def test_login_page_uses_shared_auth_shell(client):
    response = client.get(reverse("login"))

    assert response.status_code == 200
    content = response.content.decode()
    assert 'class="auth-shell"' in content
    assert 'class="auth-card"' in content


def test_authenticated_page_uses_shared_crm_shell(client, db):
    user = get_user_model().objects.create_user(
        email="shell@example.com",
        password="password123",
    )
    client.force_login(user)

    response = client.get(reverse("crm:user_dashboard"))

    assert response.status_code == 200
    content = response.content.decode()
    assert 'class="app-shell"' in content
    assert 'class="sidebar"' in content
    assert 'class="content-shell"' in content


def test_docker_compose_runs_entrypoint_via_shell():
    compose_text = Path("docker-compose.yml").read_text()

    assert "command: sh /app/entrypoint.sh" in compose_text


def test_docker_compose_overrides_database_url_for_container_network():
    compose_text = Path("docker-compose.yml").read_text()

    assert "DATABASE_URL=postgres://factflow:factflow@db:5432/factflow" not in compose_text
