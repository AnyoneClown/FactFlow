from io import BytesIO

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from openpyxl import Workbook

from apps.imports.models import ImportedFact, UploadLog

REQUIRED_HEADERS = [
    "Advertiser",
    "Brand",
    "Start",
    "End",
    "Format",
    "Platform",
    "Impr",
]


def make_upload(rows, filename="facts.xlsx", headers=None):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "rnd2"
    if headers is not None:
        sheet.append(headers)
    for row in rows:
        sheet.append(row)
    payload = BytesIO()
    workbook.save(payload)
    payload.seek(0)
    return SimpleUploadedFile(
        filename,
        payload.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(
        email="user@example.com",
        password="password123",
    )


@pytest.mark.django_db
def test_upload_import_creates_success_log_and_imported_facts(client, user):
    client.force_login(user)
    upload = make_upload(
        [
            ["Acme", "RoadRunner", "2024-01-01", "2024-01-31", "Video", "YouTube", 500],
            ["Acme", "Coyote", "2024-02-01", "2024-02-29", "Banner", "Meta", 700],
        ],
        headers=REQUIRED_HEADERS,
    )

    response = client.post(reverse("crm:upload"), {"file": upload}, follow=True)

    assert response.status_code == 200
    log = UploadLog.objects.get()
    assert log.user == user
    assert log.status == UploadLog.Status.SUCCESS
    assert log.total_rows == 2
    assert log.success_rows == 2
    assert log.failed_rows == 0
    assert log.error_type in (None, "")
    assert ImportedFact.objects.filter(user=user).count() == 2
    assert "success" in response.content.decode().lower()


@pytest.mark.django_db
def test_upload_import_marks_partial_success_when_some_rows_are_invalid(client, user):
    client.force_login(user)
    upload = make_upload(
        [
            ["Acme", "RoadRunner", "2024-01-01", "2024-01-31", "Video", "YouTube", 500],
            ["Acme", "RoadRunner", "", "2024-01-31", "Video", "YouTube", 600],
        ],
        headers=REQUIRED_HEADERS,
    )

    response = client.post(reverse("crm:upload"), {"file": upload}, follow=True)

    assert response.status_code == 200
    log = UploadLog.objects.get()
    assert log.status == UploadLog.Status.PARTIAL_SUCCESS
    assert log.error_type == UploadLog.ErrorType.INVALID_ROW_DATA
    assert log.total_rows == 2
    assert log.success_rows == 1
    assert log.failed_rows == 1
    assert ImportedFact.objects.count() == 1
    assert "partial_success" in response.content.decode()


@pytest.mark.django_db
def test_upload_import_marks_failed_when_no_valid_rows_are_found(client, user):
    client.force_login(user)
    upload = make_upload(
        [["Acme", "RoadRunner", "", "", "Video", "YouTube", "bad"]],
        headers=REQUIRED_HEADERS,
    )

    response = client.post(reverse("crm:upload"), {"file": upload}, follow=True)

    assert response.status_code == 200
    log = UploadLog.objects.get()
    assert log.status == UploadLog.Status.FAILED
    assert log.error_type == UploadLog.ErrorType.NO_VALID_ROWS
    assert log.total_rows == 1
    assert log.success_rows == 0
    assert log.failed_rows == 1
    assert ImportedFact.objects.count() == 0
    assert "failed" in response.content.decode().lower()


@pytest.mark.django_db
def test_upload_import_rejects_missing_required_columns(client, user):
    client.force_login(user)
    upload = make_upload(
        [["Acme", "RoadRunner"]],
        headers=["Advertiser", "Brand"],
    )

    response = client.post(reverse("crm:upload"), {"file": upload}, follow=True)

    assert response.status_code == 200
    log = UploadLog.objects.get()
    assert log.status == UploadLog.Status.FAILED
    assert log.error_type == UploadLog.ErrorType.MISSING_REQUIRED_COLUMNS
    assert ImportedFact.objects.count() == 0
    assert "Missing required columns" in response.content.decode()
