from django.contrib.auth import get_user_model
from django.db import models

from apps.imports.models import ImportedFact, UploadLog


def field_names(model):
    return {field.name for field in model._meta.fields}


def index_field_names(model):
    return {tuple(index.fields) for index in model._meta.indexes}


def test_upload_log_defines_required_fields_and_choices():
    assert {
        "id",
        "user",
        "original_filename",
        "uploaded_at",
        "status",
        "error_type",
        "error_message",
        "total_rows",
        "success_rows",
        "failed_rows",
    }.issubset(field_names(UploadLog))

    assert UploadLog._meta.get_field("user").remote_field.model == get_user_model()
    assert UploadLog._meta.get_field("status").default == UploadLog.Status.SUCCESS
    assert set(UploadLog.Status.values) == {
        "success",
        "partial_success",
        "failed",
    }
    assert set(UploadLog.ErrorType.values) == {
        "invalid_file_format",
        "missing_required_columns",
        "invalid_headers",
        "invalid_row_data",
        "empty_file",
        "no_valid_rows",
        "unexpected_error",
    }


def test_imported_fact_defines_required_fields_and_indexes():
    assert {
        "id",
        "upload",
        "user",
        "advertiser",
        "brand",
        "start",
        "end",
        "format",
        "platform",
        "impr",
        "created_at",
    }.issubset(field_names(ImportedFact))

    assert ImportedFact._meta.get_field("upload").remote_field.model == UploadLog
    assert ImportedFact._meta.get_field("user").remote_field.model == get_user_model()
    assert isinstance(ImportedFact._meta.get_field("impr"), models.BigIntegerField)
    assert {("start",), ("user",), ("upload",)}.issubset(
        index_field_names(ImportedFact)
    )
