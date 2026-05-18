import pytest
from django.contrib.auth import get_user_model


def test_user_model_uses_email_as_login_identifier():
    User = get_user_model()

    assert User.USERNAME_FIELD == "email"
    assert User.REQUIRED_FIELDS == []
    assert "username" not in {field.name for field in User._meta.fields}
    assert User._meta.get_field("email").unique is True


@pytest.mark.django_db
def test_user_manager_creates_user_with_email_only():
    User = get_user_model()

    user = User.objects.create_user(
        email="person@example.com",
        password="secure-password",
    )

    assert user.email == "person@example.com"
    assert user.check_password("secure-password")
    assert user.is_active is True
    assert user.is_staff is False
    assert user.is_superuser is False


@pytest.mark.django_db
def test_user_manager_creates_superuser_with_email_only():
    User = get_user_model()

    user = User.objects.create_superuser(
        email="admin@example.com",
        password="secure-password",
    )

    assert user.email == "admin@example.com"
    assert user.is_staff is True
    assert user.is_superuser is True
