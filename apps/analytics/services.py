from __future__ import annotations

from django.db.models import Avg, Count, Sum
from django.db.models.functions import ExtractYear, TruncMonth

from apps.imports.models import UploadLog


def build_statistics_dashboard(*, facts, uploads) -> dict:
    yearly_totals = list(
        facts.values("start__year")
        .annotate(total_impr=Sum("impr"))
        .order_by("start__year")
    )

    top_brands = list(
        facts.values("brand")
        .annotate(total_impr=Sum("impr"))
        .order_by("-total_impr", "brand")[:5]
    )
    top_platforms = list(
        facts.values("platform")
        .annotate(total_impr=Sum("impr"))
        .order_by("-total_impr", "platform")[:5]
    )
    top_advertisers = list(
        facts.values("advertiser")
        .annotate(total_impr=Sum("impr"))
        .order_by("-total_impr", "advertiser")[:5]
    )
    top_formats = list(
        facts.values("format")
        .annotate(total_impr=Sum("impr"))
        .order_by("-total_impr", "format")[:5]
    )
    monthly_totals = list(
        facts.annotate(month=TruncMonth("start"))
        .values("month")
        .annotate(total_impr=Sum("impr"))
        .order_by("month")
    )

    status_counts = {
        row["status"]: row["count"]
        for row in uploads.values("status").annotate(count=Count("id"))
    }
    upload_status_totals = [
        {
            "status": status,
            "label": UploadLog.Status(status).label,
            "count": status_counts.get(status, 0),
        }
        for status in (
            UploadLog.Status.SUCCESS,
            UploadLog.Status.PARTIAL_SUCCESS,
            UploadLog.Status.FAILED,
        )
        if status_counts.get(status, 0)
    ]

    summary_row = facts.aggregate(
        total_impr=Sum("impr"),
        total_rows=Count("id"),
        avg_impr=Avg("impr"),
        active_years=Count(ExtractYear("start"), distinct=True),
    )

    best_year = yearly_totals[-1]["start__year"] if yearly_totals else None
    best_year_total_impr = yearly_totals[-1]["total_impr"] if yearly_totals else 0
    if yearly_totals:
        strongest_year = max(yearly_totals, key=lambda row: row["total_impr"])
        best_year = strongest_year["start__year"]
        best_year_total_impr = strongest_year["total_impr"]

    analytics_summary = {
        "total_impr": summary_row["total_impr"] or 0,
        "total_rows": summary_row["total_rows"] or 0,
        "average_impr": int(summary_row["avg_impr"] or 0),
        "active_years": summary_row["active_years"] or 0,
        "top_brand": top_brands[0]["brand"] if top_brands else "No data",
        "top_platform": top_platforms[0]["platform"] if top_platforms else "No data",
        "best_year": best_year,
        "best_year_total_impr": best_year_total_impr,
        "total_uploads": uploads.count(),
    }

    return {
        "analytics_summary": analytics_summary,
        "yearly_totals": yearly_totals,
        "top_brands": top_brands,
        "top_platforms": top_platforms,
        "top_advertisers": top_advertisers,
        "top_formats": top_formats,
        "monthly_totals": monthly_totals,
        "upload_status_totals": upload_status_totals,
    }
