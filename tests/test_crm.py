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
def second_user(db):
    return get_user_model().objects.create_user(
        email="second@example.com",
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


def create_upload(
    user,
    filename,
    status=UploadLog.Status.SUCCESS,
    total_rows=1,
    success_rows=1,
    failed_rows=0,
    error_type="",
):
    return UploadLog.objects.create(
        user=user,
        original_filename=filename,
        status=status,
        total_rows=total_rows,
        success_rows=success_rows,
        failed_rows=failed_rows,
        error_type=error_type or None,
    )


def create_fact(user, upload, start, impr, brand="RoadRunner"):
    return ImportedFact.objects.create(
        user=user,
        upload=upload,
        advertiser="Acme",
        brand=brand,
        start=start,
        end=start,
        format="Video",
        platform="YouTube",
        impr=impr,
    )


@pytest.mark.django_db
def test_user_dashboard_shows_only_current_users_recent_uploads(
    client,
    user,
    second_user,
):
    recent_upload = create_upload(
        user,
        "recent.xlsx",
        status=UploadLog.Status.PARTIAL_SUCCESS,
        total_rows=3,
        success_rows=2,
        failed_rows=1,
        error_type=UploadLog.ErrorType.INVALID_ROW_DATA,
    )
    create_upload(
        second_user,
        "other.xlsx",
        status=UploadLog.Status.SUCCESS,
    )
    create_fact(user, recent_upload, date(2024, 1, 1), 120)
    create_fact(user, recent_upload, date(2024, 2, 1), 130, brand="Coyote")

    client.force_login(user)
    response = client.get(reverse("crm:user_dashboard"))

    assert response.status_code == 200
    assert response.context["total_uploads"] == 1
    assert response.context["total_imported_rows"] == 2
    uploads = list(response.context["recent_uploads"])
    assert len(uploads) == 1
    assert uploads[0].original_filename == "recent.xlsx"
    content = response.content.decode()
    assert "recent.xlsx" in content
    assert "other.xlsx" not in content


@pytest.mark.django_db
def test_admin_dashboard_shows_global_counts(client, admin_user, user, second_user):
    create_upload(user, "ok.xlsx", status=UploadLog.Status.SUCCESS)
    create_upload(
        second_user,
        "partial.xlsx",
        status=UploadLog.Status.PARTIAL_SUCCESS,
        total_rows=2,
        success_rows=1,
        failed_rows=1,
    )
    failed_upload = create_upload(
        admin_user,
        "failed.xlsx",
        status=UploadLog.Status.FAILED,
        total_rows=1,
        success_rows=0,
        failed_rows=1,
        error_type=UploadLog.ErrorType.NO_VALID_ROWS,
    )
    create_fact(
        user,
        UploadLog.objects.get(original_filename="ok.xlsx"),
        date(2024, 1, 1),
        100,
    )
    create_fact(
        second_user,
        UploadLog.objects.get(original_filename="partial.xlsx"),
        date(2024, 2, 1),
        200,
    )
    create_fact(admin_user, failed_upload, date(2024, 3, 1), 300, brand="AdminBrand")

    client.force_login(admin_user)
    response = client.get(reverse("crm:admin_dashboard"))

    assert response.status_code == 200
    assert response.context["total_uploads"] == 3
    assert response.context["success_uploads"] == 1
    assert response.context["partial_success_uploads"] == 1
    assert response.context["failed_uploads"] == 1
    assert response.context["total_users"] == 3
    assert response.context["total_imported_rows"] == 3


@pytest.mark.django_db
def test_admin_upload_logs_page_lists_logs_with_pagination(client, admin_user, user):
    for index in range(26):
        create_upload(
            user,
            f"file-{index}.xlsx",
            status=(
                UploadLog.Status.SUCCESS
                if index % 2 == 0
                else UploadLog.Status.FAILED
            ),
            error_type=UploadLog.ErrorType.NO_VALID_ROWS if index % 2 else "",
        )

    client.force_login(admin_user)
    response = client.get(reverse("crm:admin_upload_logs"))

    assert response.status_code == 200
    page = response.context["page_obj"]
    assert page.paginator.count == 26
    assert page.paginator.num_pages == 2
    assert len(response.context["upload_logs"]) == 25
    assert "file-25.xlsx" not in response.content.decode()


@pytest.mark.django_db
def test_admin_users_page_lists_users_with_access_levels(
    client,
    admin_user,
    user,
    second_user,
):
    client.force_login(admin_user)
    response = client.get(reverse("crm:admin_users"))

    assert response.status_code == 200
    users = list(response.context["users"])
    emails = {entry.email for entry in users}
    assert {admin_user.email, user.email, second_user.email}.issubset(emails)
    content = response.content.decode()
    assert admin_user.email in content
    assert user.email in content
    assert "Admin" in content
    assert "User" in content


@pytest.mark.django_db
def test_admin_imported_facts_page_lists_all_facts_with_pagination(
    client,
    admin_user,
    user,
    second_user,
):
    first_upload = create_upload(user, "user.xlsx")
    second_upload = create_upload(second_user, "second.xlsx")
    for index in range(26):
        owner = user if index % 2 == 0 else second_user
        upload = first_upload if index % 2 == 0 else second_upload
        create_fact(
            owner,
            upload,
            date(2024, 1, 1),
            100 + index,
            brand=f"Brand-{index}",
        )

    client.force_login(admin_user)
    response = client.get(reverse("crm:admin_imported_facts"))

    assert response.status_code == 200
    page = response.context["page_obj"]
    assert page.paginator.count == 26
    assert page.paginator.num_pages == 2
    assert len(response.context["facts"]) == 25
    content = response.content.decode()
    assert "Brand-0" in content
    assert "Brand-25" not in content
