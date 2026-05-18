import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(
        email="user@example.com",
        password="password123",
    )


@pytest.fixture
def admin_user(db):
    user = get_user_model().objects.create_user(
        email="admin@example.com",
        password="password123",
    )
    admin_group, _ = Group.objects.get_or_create(name="Admin")
    user.groups.add(admin_group)
    return user


def test_login_page_renders_email_login_form(client):
    response = client.get(reverse("login"))

    assert response.status_code == 200
    assert b'name="username"' in response.content
    assert b'type="email"' in response.content
    assert b'class="auth-shell"' in response.content
    assert b"Email or username" in response.content


def test_health_endpoint_is_public(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_user_can_login_with_email_and_logout(client, user):
    response = client.post(
        reverse("login"),
        {"username": "user@example.com", "password": "password123"},
    )

    assert response.status_code == 302
    assert response.url == reverse("crm:user_dashboard")

    response = client.post(reverse("logout"))

    assert response.status_code == 302
    assert response.url == reverse("login")


@pytest.mark.django_db
def test_unauthenticated_user_is_redirected_from_crm_pages(client):
    for url_name in ("crm:user_dashboard", "crm:upload", "crm:statistics"):
        response = client.get(reverse(url_name))

        assert response.status_code == 302
        assert response.url.startswith(f"{reverse('login')}?next=")


@pytest.mark.django_db
def test_regular_user_can_open_user_crm_pages(client, user):
    client.force_login(user)

    for url_name in ("crm:user_dashboard", "crm:upload", "crm:statistics"):
        response = client.get(reverse(url_name))

        assert response.status_code == 200


@pytest.mark.django_db
def test_regular_user_cannot_open_admin_crm_pages(client, user):
    client.force_login(user)

    for url_name in (
        "crm:admin_dashboard",
        "crm:admin_upload_logs",
        "crm:admin_users",
        "crm:admin_imported_facts",
    ):
        response = client.get(reverse(url_name))

        assert response.status_code == 403


@pytest.mark.django_db
def test_admin_group_user_can_open_admin_crm_pages(client, admin_user):
    client.force_login(admin_user)

    for url_name in (
        "crm:admin_dashboard",
        "crm:admin_upload_logs",
        "crm:admin_users",
        "crm:admin_imported_facts",
    ):
        response = client.get(reverse(url_name))

        assert response.status_code == 200
