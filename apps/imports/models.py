from django.conf import settings
from django.db import models


class UploadLog(models.Model):
    class Status(models.TextChoices):
        SUCCESS = "success", "Success"
        PARTIAL_SUCCESS = "partial_success", "Partial success"
        FAILED = "failed", "Failed"

    class ErrorType(models.TextChoices):
        INVALID_FILE_FORMAT = "invalid_file_format", "Invalid file format"
        MISSING_REQUIRED_COLUMNS = (
            "missing_required_columns",
            "Missing required columns",
        )
        INVALID_HEADERS = "invalid_headers", "Invalid headers"
        INVALID_ROW_DATA = "invalid_row_data", "Invalid row data"
        EMPTY_FILE = "empty_file", "Empty file"
        NO_VALID_ROWS = "no_valid_rows", "No valid rows"
        UNEXPECTED_ERROR = "unexpected_error", "Unexpected error"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    original_filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.SUCCESS,
    )
    error_type = models.CharField(
        max_length=64,
        choices=ErrorType.choices,
        blank=True,
        null=True,
    )
    error_message = models.TextField(blank=True, null=True)
    total_rows = models.PositiveIntegerField(default=0)
    success_rows = models.PositiveIntegerField(default=0)
    failed_rows = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "import_upload_logs"
        verbose_name = "upload log"
        verbose_name_plural = "upload logs"

    def __str__(self) -> str:
        return f"{self.original_filename} ({self.status})"


class ImportedFact(models.Model):
    upload = models.ForeignKey(
        UploadLog,
        on_delete=models.CASCADE,
        related_name="facts",
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    advertiser = models.CharField(max_length=255)
    brand = models.CharField(max_length=255)
    start = models.DateField()
    end = models.DateField()
    format = models.CharField(max_length=128)
    platform = models.CharField(max_length=128)
    impr = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "imported_facts"
        verbose_name = "imported fact"
        verbose_name_plural = "imported facts"
        indexes = [
            models.Index(fields=["start"]),
            models.Index(fields=["user"]),
            models.Index(fields=["upload"]),
        ]

    def __str__(self) -> str:
        return f"{self.brand} on {self.platform} from {self.start}"
