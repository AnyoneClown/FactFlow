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


def create_fact(
    user,
    upload,
    start,
    impr,
    advertiser="Acme",
    brand="RoadRunner",
    platform="YouTube",
    format="Video",
):
    return ImportedFact.objects.create(
        user=user,
        upload=upload,
        advertiser=advertiser,
        brand=brand,
        start=start,
        end=start,
        format=format,
        platform=platform,
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
    summary = response.context["analytics_summary"]
    assert summary["total_impr"] == 325
    assert summary["total_rows"] == 3
    assert summary["top_brand"] == "RoadRunner"
    assert summary["top_platform"] == "YouTube"
    assert list(response.context["upload_status_totals"]) == [
        {"status": UploadLog.Status.SUCCESS, "label": "Success", "count": 1}
    ]
    content = response.content.decode()
    assert "Performance snapshot" in content
    assert "Top brands" in content
    assert "Upload health" in content
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
    create_fact(
        user,
        user_upload,
        date(2024, 3, 1),
        100,
        brand="Launch Fuel",
        platform="Meta",
    )
    create_fact(
        other_user,
        other_upload,
        date(2025, 1, 1),
        300,
        advertiser="Globex",
        brand="Future Wave",
        platform="TikTok",
        format="Display",
    )

    client.force_login(admin_user)
    response = client.get(reverse("crm:statistics"))

    assert response.status_code == 200
    aggregates = list(response.context["yearly_totals"])
    assert aggregates == [
        {"start__year": 2024, "total_impr": 150},
        {"start__year": 2025, "total_impr": 300},
    ]
    summary = response.context["analytics_summary"]
    assert summary["total_impr"] == 450
    assert summary["top_brand"] == "Future Wave"
    assert summary["top_platform"] == "TikTok"
    assert summary["best_year"] == 2025
    assert summary["best_year_total_impr"] == 300
    assert list(response.context["top_brands"]) == [
        {"brand": "Future Wave", "total_impr": 300},
        {"brand": "Launch Fuel", "total_impr": 100},
        {"brand": "RoadRunner", "total_impr": 50},
    ]
    assert list(response.context["top_platforms"]) == [
        {"platform": "TikTok", "total_impr": 300},
        {"platform": "Meta", "total_impr": 100},
        {"platform": "YouTube", "total_impr": 50},
    ]
    assert list(response.context["top_advertisers"]) == [
        {"advertiser": "Globex", "total_impr": 300},
        {"advertiser": "Acme", "total_impr": 150},
    ]
    content = response.content.decode()
    assert "Future Wave" in content
    assert "Globex" in content
    assert "TikTok" in content
    assert "150" in content
    assert "300" in content


@pytest.mark.django_db
def test_statistics_page_builds_dashboard_sections_for_mixed_upload_health(
    client,
    user,
):
    good_upload = create_upload(user, "good.xlsx")
    partial_upload = UploadLog.objects.create(
        user=user,
        original_filename="partial.xlsx",
        status=UploadLog.Status.PARTIAL_SUCCESS,
        total_rows=4,
        success_rows=3,
        failed_rows=1,
        error_type=UploadLog.ErrorType.INVALID_ROW_DATA,
    )
    UploadLog.objects.create(
        user=user,
        original_filename="failed.xlsx",
        status=UploadLog.Status.FAILED,
        total_rows=2,
        success_rows=0,
        failed_rows=2,
        error_type=UploadLog.ErrorType.NO_VALID_ROWS,
    )
    create_fact(
        user,
        good_upload,
        date(2024, 1, 1),
        110,
        brand="Brand A",
        platform="YouTube",
    )
    create_fact(
        user,
        partial_upload,
        date(2024, 2, 1),
        90,
        brand="Brand B",
        platform="Meta",
        format="Display",
    )
    create_fact(
        user,
        partial_upload,
        date(2024, 3, 1),
        60,
        brand="Brand B",
        platform="Meta",
        format="Display",
    )

    client.force_login(user)
    response = client.get(reverse("crm:statistics"))

    assert response.status_code == 200
    assert list(response.context["upload_status_totals"]) == [
        {"status": UploadLog.Status.SUCCESS, "label": "Success", "count": 1},
        {
            "status": UploadLog.Status.PARTIAL_SUCCESS,
            "label": "Partial success",
            "count": 1,
        },
        {"status": UploadLog.Status.FAILED, "label": "Failed", "count": 1},
    ]
    assert list(response.context["top_formats"]) == [
        {"format": "Display", "total_impr": 150},
        {"format": "Video", "total_impr": 110},
    ]
    assert list(response.context["monthly_totals"]) == [
        {"month": date(2024, 1, 1), "total_impr": 110},
        {"month": date(2024, 2, 1), "total_impr": 90},
        {"month": date(2024, 3, 1), "total_impr": 60},
    ]
    content = response.content.decode()
    assert "Brand B" in content
    assert "Display" in content
    assert "partial success" in content.lower()
