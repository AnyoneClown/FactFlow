from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import FormView, ListView, TemplateView

from apps.analytics.services import build_statistics_dashboard
from apps.imports.models import ImportedFact, UploadLog
from apps.imports.services import import_fact_file

from .forms import UploadFileForm
from .roles import ADMIN_GROUP_NAME, AdminRequiredMixin, is_admin


class UserDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "crm/user_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        uploads = (
            UploadLog.objects.filter(user=self.request.user)
            .order_by("-uploaded_at")
        )
        context["total_uploads"] = uploads.count()
        context["total_imported_rows"] = ImportedFact.objects.filter(
            user=self.request.user
        ).count()
        context["recent_uploads"] = uploads[:5]
        return context


class UploadView(LoginRequiredMixin, FormView):
    template_name = "crm/upload.html"
    form_class = UploadFileForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["latest_upload"] = (
            UploadLog.objects.filter(user=self.request.user)
            .order_by("-uploaded_at")
            .first()
        )
        return context

    def form_valid(self, form):
        result = import_fact_file(self.request.user, form.cleaned_data["file"])
        status = result.upload_log.status
        if status == UploadLog.Status.SUCCESS:
            messages.success(self.request, "Import finished with status success.")
        elif status == UploadLog.Status.PARTIAL_SUCCESS:
            messages.warning(
                self.request,
                (
                    "Import finished with status partial_success. "
                    f"{result.upload_log.error_message}"
                ),
            )
        else:
            detail = (
                f" {result.upload_log.error_message}"
                if result.upload_log.error_message
                else ""
            )
            messages.error(
                self.request,
                f"Import finished with status failed.{detail}",
            )
        return redirect("crm:upload")


class StatisticsView(LoginRequiredMixin, TemplateView):
    template_name = "crm/statistics.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        facts = ImportedFact.objects.all()
        uploads = UploadLog.objects.all()
        if not is_admin(self.request.user):
            facts = facts.filter(user=self.request.user)
            uploads = uploads.filter(user=self.request.user)
        context.update(build_statistics_dashboard(facts=facts, uploads=uploads))
        context["showing_all_data"] = is_admin(self.request.user)
        return context


class AdminDashboardView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    template_name = "crm/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_uploads"] = UploadLog.objects.count()
        context["success_uploads"] = UploadLog.objects.filter(
            status=UploadLog.Status.SUCCESS
        ).count()
        context["partial_success_uploads"] = UploadLog.objects.filter(
            status=UploadLog.Status.PARTIAL_SUCCESS
        ).count()
        context["failed_uploads"] = UploadLog.objects.filter(
            status=UploadLog.Status.FAILED
        ).count()
        context["total_users"] = self.request.user.__class__.objects.count()
        context["total_imported_rows"] = ImportedFact.objects.count()
        return context


class AdminUploadLogsView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    template_name = "crm/upload_logs.html"
    context_object_name = "upload_logs"
    paginate_by = 25

    def get_queryset(self):
        return UploadLog.objects.select_related("user").order_by("uploaded_at", "id")


class AdminUsersView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    template_name = "crm/users.html"
    context_object_name = "users"
    paginate_by = 25

    def get_queryset(self):
        users = list(self.request.user.__class__.objects.order_by("-date_joined"))
        for user in users:
            user.access_level = (
                "Admin"
                if user.is_superuser
                or user.groups.filter(name=ADMIN_GROUP_NAME).exists()
                else "User"
            )
        return users


class AdminImportedFactsView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    template_name = "crm/imported_facts.html"
    context_object_name = "facts"
    paginate_by = 25

    def get_queryset(self):
        return ImportedFact.objects.select_related("user", "upload").order_by(
            "created_at",
            "id",
        )
