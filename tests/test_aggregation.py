from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from apps.imports.models import ImportedFact, UploadLog


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(
        email="user@example.com",
        password="password123",
    )


@pytest.fixture
def other_user(db):
    return get_user_model().objects.create_user(
        email="other@example.com",
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


def create_upload(user, filename="facts.xlsx"):
    return UploadLog.objects.create(
        user=user,
        original_filename=filename,
        status=UploadLog.Status.SUCCESS,
        total_rows=1,
        success_rows=1,
        failed_rows=0,
    )


def create_fact(user, upload, start, impr):
    return ImportedFact.objects.create(
        user=user,
        upload=upload,
        advertiser="Acme",
        brand="RoadRunner",
        start=start,
        end=start,
        format="Video",
        platform="YouTube",
        impr=impr,
    )


@pytest.mark.django_db
def test_statistics_page_aggregates_impr_by_year_for_regular_user(
    client,
    user,
    other_user,
):
    user_upload = create_upload(user, "user.xlsx")
    other_upload = create_upload(other_user, "other.xlsx")
    create_fact(user, user_upload, date(2023, 1, 10), 100)
    create_fact(user, user_upload, date(2023, 7, 10), 150)
    create_fact(user, user_upload, date(2024, 2, 5), 75)
    create_fact(other_user, other_upload, date(2023, 3, 3), 999)

    client.force_login(user)
    response = client.get(reverse("crm:statistics"))

    assert response.status_code == 200
    aggregates = list(response.context["yearly_totals"])
    assert aggregates == [
        {"start__year": 2023, "total_impr": 250},
        {"start__year": 2024, "total_impr": 75},
    ]
    content = response.content.decode()
    assert "2023" in content
    assert "250" in content
    assert "999" not in content


@pytest.mark.django_db
def test_statistics_page_shows_all_users_data_for_admin(
    client,
    admin_user,
    user,
    other_user,
):
    admin_upload = create_upload(admin_user, "admin.xlsx")
    user_upload = create_upload(user, "user.xlsx")
    other_upload = create_upload(other_user, "other.xlsx")
    create_fact(admin_user, admin_upload, date(2024, 1, 1), 50)
    create_fact(user, user_upload, date(2024, 3, 1), 100)
    create_fact(other_user, other_upload, date(2025, 1, 1), 300)

    client.force_login(admin_user)
    response = client.get(reverse("crm:statistics"))

    assert response.status_code == 200
    aggregates = list(response.context["yearly_totals"])
    assert aggregates == [
        {"start__year": 2024, "total_impr": 150},
        {"start__year": 2025, "total_impr": 300},
    ]
    content = response.content.decode()
    assert "150" in content
    assert "300" in content
