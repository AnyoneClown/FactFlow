from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pandas as pd
from django.db import transaction

from .models import ImportedFact, UploadLog

REQUIRED_COLUMNS = {
    "advertiser": "Advertiser",
    "brand": "Brand",
    "start": "Start",
    "end": "End",
    "format": "Format",
    "platform": "Platform",
    "impr": "Impr",
}
SUPPORTED_EXTENSIONS = {".xlsx", ".xls", ".csv"}


@dataclass(frozen=True)
class ParsedFactRow:
    advertiser: str
    brand: str
    start: date
    end: date
    format: str
    platform: str
    impr: int


@dataclass(frozen=True)
class RowValidationError:
    row_number: int
    message: str


@dataclass(frozen=True)
class ParseResult:
    valid_rows: list[ParsedFactRow] = field(default_factory=list)
    row_errors: list[RowValidationError] = field(default_factory=list)
    total_rows: int = 0

    @property
    def success_rows(self) -> int:
        return len(self.valid_rows)

    @property
    def failed_rows(self) -> int:
        return len(self.row_errors)


class SpreadsheetParseError(ValueError):
    def __init__(self, error_type: str, message: str) -> None:
        super().__init__(message)
        self.error_type = error_type


@dataclass(frozen=True)
class ImportResult:
    upload_log: UploadLog
    imported_count: int


def parse_fact_file(
    file: str | Path | BinaryIO,
    filename: str | None = None,
) -> ParseResult:
    """Parse a FactFlow input file into validated rows and row-level errors."""
    source_name = filename or getattr(file, "name", "") or str(file)
    extension = Path(source_name).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise SpreadsheetParseError(
            UploadLog.ErrorType.INVALID_FILE_FORMAT,
            f"Unsupported file format: {extension or 'unknown'}",
        )

    raw_rows = (
        _read_csv_rows(file)
        if extension == ".csv"
        else _read_excel_rows(
            file,
            engine="xlrd" if extension == ".xls" else "openpyxl",
        )
    )

    return _parse_rows(raw_rows)


def import_fact_file(user, uploaded_file) -> ImportResult:
    filename = getattr(uploaded_file, "name", "upload")

    try:
        parsed = parse_fact_file(uploaded_file, filename)
    except SpreadsheetParseError as exc:
        upload_log = UploadLog.objects.create(
            user=user,
            original_filename=filename,
            status=UploadLog.Status.FAILED,
            error_type=exc.error_type,
            error_message=str(exc),
        )
        return ImportResult(upload_log=upload_log, imported_count=0)

    if parsed.success_rows == 0:
        upload_log = UploadLog.objects.create(
            user=user,
            original_filename=filename,
            status=UploadLog.Status.FAILED,
            error_type=UploadLog.ErrorType.NO_VALID_ROWS,
            error_message=_build_row_error_message(parsed),
            total_rows=parsed.total_rows,
            success_rows=0,
            failed_rows=parsed.failed_rows,
        )
        return ImportResult(upload_log=upload_log, imported_count=0)

    status = UploadLog.Status.SUCCESS
    error_type = None
    error_message = ""
    if parsed.failed_rows:
        status = UploadLog.Status.PARTIAL_SUCCESS
        error_type = UploadLog.ErrorType.INVALID_ROW_DATA
        error_message = _build_row_error_message(parsed)

    with transaction.atomic():
        upload_log = UploadLog.objects.create(
            user=user,
            original_filename=filename,
            status=status,
            error_type=error_type,
            error_message=error_message,
            total_rows=parsed.total_rows,
            success_rows=parsed.success_rows,
            failed_rows=parsed.failed_rows,
        )
        ImportedFact.objects.bulk_create(
            [
                ImportedFact(
                    upload=upload_log,
                    user=user,
                    advertiser=row.advertiser,
                    brand=row.brand,
                    start=row.start,
                    end=row.end,
                    format=row.format,
                    platform=row.platform,
                    impr=row.impr,
                )
                for row in parsed.valid_rows
            ]
        )

    return ImportResult(upload_log=upload_log, imported_count=parsed.success_rows)


def _parse_rows(rows: list[list[object]]) -> ParseResult:
    if not rows:
        raise SpreadsheetParseError(UploadLog.ErrorType.EMPTY_FILE, "File is empty.")

    header_row = rows[0]
    header_map = _build_header_map(header_row)
    if not header_map:
        raise SpreadsheetParseError(
            UploadLog.ErrorType.INVALID_HEADERS,
            "Header row is empty or invalid.",
        )

    missing = [
        canonical
        for normalized, canonical in REQUIRED_COLUMNS.items()
        if normalized not in header_map
    ]
    if missing:
        missing_text = ", ".join(missing)
        raise SpreadsheetParseError(
            UploadLog.ErrorType.MISSING_REQUIRED_COLUMNS,
            f"Missing required columns: {missing_text}",
        )

    valid_rows: list[ParsedFactRow] = []
    row_errors: list[RowValidationError] = []

    for index, row in enumerate(rows[1:], start=2):
        if all(value in (None, "") for value in row):
            continue
        try:
            valid_rows.append(_parse_data_row(row, header_map))
        except ValueError as exc:
            row_errors.append(RowValidationError(row_number=index, message=str(exc)))

    return ParseResult(
        valid_rows=valid_rows,
        row_errors=row_errors,
        total_rows=len(valid_rows) + len(row_errors),
    )


def _build_row_error_message(parsed: ParseResult) -> str:
    return " | ".join(
        f"Row {row_error.row_number}: {row_error.message}"
        for row_error in parsed.row_errors
    )


def _read_excel_rows(file: str | Path | BinaryIO, engine: str) -> list[list[object]]:
    try:
        seek = getattr(file, "seek", None)
        if seek:
            seek(0)
        sheets = pd.read_excel(
            file,
            sheet_name=None,
            header=None,
            dtype=object,
            engine=engine,
        )
    except Exception as exc:
        raise SpreadsheetParseError(
            UploadLog.ErrorType.INVALID_FILE_FORMAT,
            "Could not read Excel workbook.",
        ) from exc

    values = getattr(sheets, "values", None)
    if callable(values):
        sheet = sheets.get("rnd2")
        if sheet is None:
            sheet = next(iter(values()))
    else:
        sheet = sheets
    return _dataframe_to_rows(sheet)


def _read_csv_rows(file: str | Path | BinaryIO) -> list[list[object]]:
    try:
        raw = Path(file).read_bytes()
    except TypeError:
        seek = getattr(file, "seek", None)
        if seek:
            seek(0)
        raw = file.read()

    for encoding in ("utf-8-sig", "utf-8", "cp1251"):
        try:
            dataframe = pd.read_csv(
                BytesIO(raw),
                encoding=encoding,
                header=None,
                dtype=object,
                keep_default_na=False,
                sep=None,
                engine="python",
            )
            return _dataframe_to_rows(dataframe)
        except UnicodeDecodeError:
            continue
        except pd.errors.EmptyDataError:
            return []
    else:
        raise SpreadsheetParseError(
            UploadLog.ErrorType.INVALID_FILE_FORMAT,
            "Could not decode CSV as UTF-8 or Windows-1251.",
        )


def _parse_data_row(row: list[object], header_map: dict[str, int]) -> ParsedFactRow:
    errors: list[str] = []
    values = {
        key: row[index] if index < len(row) else None
        for key, index in header_map.items()
    }
    advertiser = (
        str(values["advertiser"]).strip()
        if values["advertiser"] is not None
        else ""
    )
    brand = str(values["brand"]).strip() if values["brand"] is not None else ""
    ad_format = str(values["format"]).strip() if values["format"] is not None else ""
    platform = str(values["platform"]).strip() if values["platform"] is not None else ""

    for field_name, value in (
        ("Advertiser", advertiser),
        ("Brand", brand),
        ("Format", ad_format),
        ("Platform", platform),
    ):
        if not value:
            errors.append(f"{field_name} is required")

    start = _parse_date(values["start"], "Start", errors)
    end = _parse_date(values["end"], "End", errors)
    impr = _parse_impr(values["impr"], errors)

    if start and end and end < start:
        errors.append("End cannot be earlier than Start")

    if errors:
        raise ValueError("; ".join(errors))

    return ParsedFactRow(
        advertiser=advertiser,
        brand=brand,
        start=start,
        end=end,
        format=ad_format,
        platform=platform,
        impr=impr,
    )


def _parse_date(value: object, field_name: str, errors: list[str]) -> date | None:
    if value in (None, ""):
        errors.append(f"{field_name} is required")
        return None
    if type(value) is time:
        errors.append(f"{field_name} must be a valid date")
        return None

    try:
        serial = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        serial = None
    if serial is not None and Decimal(0) < serial <= Decimal(100000):
        return (datetime(1899, 12, 30) + timedelta(days=float(serial))).date()

    clean_value = str(value).strip()
    for date_format in ("%Y-%m-%d", "%d.%m.%Y", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return pd.to_datetime(
                clean_value,
                errors="raise",
                format=date_format,
            ).date()
        except (TypeError, ValueError):
            continue

    try:
        parsed = pd.to_datetime(value, errors="raise")
    except (TypeError, ValueError):
        parsed = None
    if parsed is not None and not pd.isna(parsed):
        return parsed.date()

    errors.append(f"{field_name} must be a valid date")
    return None


def _parse_impr(value: object, errors: list[str]) -> int | None:
    if value in (None, ""):
        errors.append("Impr is required")
        return None
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        errors.append("Impr must be a number")
        return None
    if number != number.to_integral_value():
        errors.append("Impr must be a whole number")
        return None
    return int(number)


def _build_header_map(header_row: list[object]) -> dict[str, int]:
    header_map: dict[str, int] = {}
    for index, header in enumerate(header_row):
        normalized = str(header).strip().lower() if header is not None else ""
        if normalized and normalized not in header_map:
            header_map[normalized] = index
    return header_map


def _dataframe_to_rows(dataframe: pd.DataFrame) -> list[list[object]]:
    rows: list[list[object]] = []
    if list(dataframe.columns) != list(range(len(dataframe.columns))):
        rows.append(
            [
                None if pd.isna(column) else column
                for column in dataframe.columns.tolist()
            ]
        )
    rows.extend(
        [None if pd.isna(value) else value for value in row]
        for row in dataframe.itertuples(index=False, name=None)
    )
    return rows
