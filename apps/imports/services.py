from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pandas as pd

from .models import UploadLog

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


def parse_fact_file(
    file: str | Path | BinaryIO,
    filename: str | None = None,
) -> ParseResult:
    """Parse a FactFlow input file into validated rows and row-level errors."""
    source_name = filename or _source_name(file)
    extension = Path(source_name).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise SpreadsheetParseError(
            UploadLog.ErrorType.INVALID_FILE_FORMAT,
            f"Unsupported file format: {extension or 'unknown'}",
        )

    if extension == ".csv":
        raw_rows = _read_csv_rows(file)
    elif extension == ".xls":
        raw_rows = _read_xls_rows(file)
    else:
        raw_rows = _read_xlsx_rows(file)

    return _parse_rows(raw_rows)


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
        if _is_blank_row(row):
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


def _read_xlsx_rows(file: str | Path | BinaryIO) -> list[list[object]]:
    return _read_excel_rows(file, engine="openpyxl")


def _read_xls_rows(file: str | Path | BinaryIO) -> list[list[object]]:
    return _read_excel_rows(file, engine="xlrd")


def _read_excel_rows(file: str | Path | BinaryIO, engine: str) -> list[list[object]]:
    try:
        _seek_start(file)
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

    sheet = sheets.get("rnd2") if isinstance(sheets, dict) else sheets
    if sheet is None:
        sheet = next(iter(sheets.values()))
    return _dataframe_to_rows(sheet)


def _read_csv_rows(file: str | Path | BinaryIO) -> list[list[object]]:
    raw = _read_file_bytes(file)
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
    advertiser = _clean_text(_row_value(row, header_map["advertiser"]))
    brand = _clean_text(_row_value(row, header_map["brand"]))
    ad_format = _clean_text(_row_value(row, header_map["format"]))
    platform = _clean_text(_row_value(row, header_map["platform"]))

    for field_name, value in (
        ("Advertiser", advertiser),
        ("Brand", brand),
        ("Format", ad_format),
        ("Platform", platform),
    ):
        if not value:
            errors.append(f"{field_name} is required")

    start = _parse_date(_row_value(row, header_map["start"]), "Start", errors)
    end = _parse_date(_row_value(row, header_map["end"]), "End", errors)
    impr = _parse_impr(_row_value(row, header_map["impr"]), errors)

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
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, time):
        errors.append(f"{field_name} must be a valid date")
        return None
    if isinstance(value, int | float | Decimal):
        serial = float(value)
        if serial <= 0:
            errors.append(f"{field_name} must be a valid date")
            return None
        return (datetime(1899, 12, 30) + timedelta(days=serial)).date()
    if isinstance(value, str):
        clean_value = value.strip()
        for date_format in ("%Y-%m-%d", "%d.%m.%Y", "%m/%d/%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(clean_value, date_format).date()
            except ValueError:
                continue
    errors.append(f"{field_name} must be a valid date")
    return None


def _parse_impr(value: object, errors: list[str]) -> int | None:
    if value in (None, ""):
        errors.append("Impr is required")
        return None
    try:
        number = Decimal(str(value).strip() if isinstance(value, str) else value)
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
        normalized = _normalize_header(header)
        if normalized and normalized not in header_map:
            header_map[normalized] = index
    return header_map


def _normalize_header(value: object) -> str:
    return str(value).strip().lower() if value is not None else ""


def _row_value(row: list[object], index: int) -> object:
    return row[index] if index < len(row) else None


def _clean_text(value: object) -> str:
    return str(value).strip() if value is not None else ""


def _is_blank_row(row: list[object]) -> bool:
    return all(value in (None, "") for value in row)


def _dataframe_to_rows(dataframe: pd.DataFrame) -> list[list[object]]:
    rows: list[list[object]] = []
    if not _has_default_columns(dataframe):
        rows.append([_normalize_cell(column) for column in dataframe.columns.tolist()])
    rows.extend(
        [_normalize_cell(value) for value in row]
        for row in dataframe.itertuples(index=False, name=None)
    )
    return rows


def _has_default_columns(dataframe: pd.DataFrame) -> bool:
    return list(dataframe.columns) == list(range(len(dataframe.columns)))


def _normalize_cell(value: object) -> object:
    if pd.isna(value):
        return None
    return value


def _read_file_bytes(file: str | Path | BinaryIO) -> bytes:
    if isinstance(file, str | Path):
        return Path(file).read_bytes()
    _seek_start(file)
    return file.read()


def _seek_start(file: BinaryIO) -> None:
    try:
        file.seek(0)
    except (AttributeError, OSError):
        pass


def _source_name(file: str | Path | BinaryIO) -> str:
    if isinstance(file, str | Path):
        return str(file)
    return getattr(file, "name", "")
