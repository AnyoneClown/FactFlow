from datetime import date
from io import BytesIO

import pandas as pd
import pytest
from openpyxl import Workbook

from apps.imports import services
from apps.imports.models import UploadLog
from apps.imports.services import SpreadsheetParseError, parse_fact_file

REQUIRED_HEADERS = [
    "Advertiser",
    "Brand",
    "Start",
    "End",
    "Format",
    "Platform",
    "Impr",
]


def make_workbook(rows, headers=None, sheet_name="rnd2"):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = sheet_name
    if headers is not None:
        sheet.append(headers)
    for row in rows:
        sheet.append(row)
    file_obj = BytesIO()
    workbook.save(file_obj)
    file_obj.seek(0)
    return file_obj


def test_parse_xlsx_reads_template_columns():
    file_obj = make_workbook(
        [
            [
                "Acme",
                "RoadRunner",
                date(2024, 1, 1),
                date(2024, 1, 31),
                "Video",
                "YouTube",
                1200,
            ]
        ],
        headers=REQUIRED_HEADERS,
    )

    result = parse_fact_file(file_obj, "facts.xlsx")

    assert result.total_rows == 1
    assert result.failed_rows == 0
    assert result.valid_rows[0].advertiser == "Acme"
    assert result.valid_rows[0].brand == "RoadRunner"
    assert result.valid_rows[0].start == date(2024, 1, 1)
    assert result.valid_rows[0].end == date(2024, 1, 31)
    assert result.valid_rows[0].impr == 1200


def test_parse_xlsx_uses_pandas_excel_reader(monkeypatch):
    calls = {}

    def fake_read_excel(file, **kwargs):
        calls["file"] = file
        calls["kwargs"] = kwargs
        return pd.DataFrame(
            [
                {
                    "Advertiser": "Acme",
                    "Brand": "RoadRunner",
                    "Start": "2024-01-01",
                    "End": "2024-01-31",
                    "Format": "Video",
                    "Platform": "YouTube",
                    "Impr": 1200,
                }
            ]
        )

    monkeypatch.setattr(services.pd, "read_excel", fake_read_excel)

    result = parse_fact_file(BytesIO(b"not a real workbook"), "facts.xlsx")

    assert result.success_rows == 1
    assert calls["kwargs"]["sheet_name"] is None
    assert calls["kwargs"]["dtype"] is object


def test_parse_xlsx_maps_reordered_columns_by_header_name():
    headers = ["Impr", "Platform", "Format", "End", "Start", "Brand", "Advertiser"]
    file_obj = make_workbook(
        [[987, "Meta", "Banner", date(2024, 2, 29), date(2024, 2, 1), "Brand", "Adv"]],
        headers=headers,
    )

    result = parse_fact_file(file_obj, "facts.xlsx")

    assert result.valid_rows[0].advertiser == "Adv"
    assert result.valid_rows[0].brand == "Brand"
    assert result.valid_rows[0].platform == "Meta"
    assert result.valid_rows[0].impr == 987


def test_parse_csv_reads_utf8_and_windows_1251_fallback():
    csv_data = (
        "Advertiser,Brand,Start,End,Format,Platform,Impr\n"
        "Реклама,Бренд,2024-03-01,2024-03-31,Video,TikTok,44\n"
    )
    file_obj = BytesIO(csv_data.encode("cp1251"))

    result = parse_fact_file(file_obj, "facts.csv")

    assert result.total_rows == 1
    assert result.valid_rows[0].advertiser == "Реклама"
    assert result.valid_rows[0].brand == "Бренд"
    assert result.valid_rows[0].start == date(2024, 3, 1)


def test_parse_file_rejects_missing_required_columns():
    file_obj = make_workbook([["Acme", "RoadRunner"]], headers=["Advertiser", "Brand"])

    with pytest.raises(SpreadsheetParseError) as exc_info:
        parse_fact_file(file_obj, "facts.xlsx")

    assert exc_info.value.error_type == UploadLog.ErrorType.MISSING_REQUIRED_COLUMNS
    assert "Start" in str(exc_info.value)


def test_parse_file_rejects_empty_file():
    file_obj = make_workbook([], headers=None)

    with pytest.raises(SpreadsheetParseError) as exc_info:
        parse_fact_file(file_obj, "facts.xlsx")

    assert exc_info.value.error_type == UploadLog.ErrorType.EMPTY_FILE


def test_parse_file_collects_invalid_rows_without_failing_valid_rows():
    file_obj = make_workbook(
        [
            [
                "Acme",
                "RoadRunner",
                "2024-01-01",
                "2024-01-31",
                "Video",
                "YouTube",
                "500",
            ],
            ["", "RoadRunner", "not-a-date", "2024-01-31", "Video", "YouTube", "oops"],
            [
                "Acme",
                "RoadRunner",
                "2024-03-31",
                "2024-03-01",
                "Video",
                "YouTube",
                "10",
            ],
        ],
        headers=REQUIRED_HEADERS,
    )

    result = parse_fact_file(file_obj, "facts.xlsx")

    assert result.total_rows == 3
    assert result.success_rows == 1
    assert result.failed_rows == 2
    assert len(result.row_errors) == 2
    assert any("Advertiser is required" in error.message for error in result.row_errors)
    assert any(
        "End cannot be earlier than Start" in error.message
        for error in result.row_errors
    )


def test_parse_workbook_with_blank_dates_does_not_crash():
    file_obj = make_workbook(
        [
            ["Acme", "RoadRunner", "", "2024-01-31", "Video", "YouTube", 500],
            ["Acme", "RoadRunner", "2024-02-01", None, "Video", "YouTube", 600],
        ],
        headers=REQUIRED_HEADERS,
    )

    result = parse_fact_file(file_obj, "facts.xlsx")

    assert result.total_rows > 0
    assert result.success_rows + result.failed_rows == result.total_rows
    assert result.failed_rows == 2
