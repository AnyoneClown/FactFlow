from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.shortcuts import redirect
from django.views.generic import FormView, TemplateView

from apps.imports.models import ImportedFact, UploadLog
from apps.imports.services import import_fact_file

from .forms import UploadFileForm
from .roles import AdminRequiredMixin, is_admin


class UserDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "crm/user_dashboard.html"


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
        if not is_admin(self.request.user):
            facts = facts.filter(user=self.request.user)
        context["yearly_totals"] = facts.values("start__year").annotate(
            total_impr=Sum("impr")
        ).order_by("start__year")
        context["showing_all_data"] = is_admin(self.request.user)
        return context


class AdminDashboardView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    template_name = "crm/dashboard.html"


class AdminUploadLogsView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    template_name = "crm/upload_logs.html"


class AdminUsersView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    template_name = "crm/users.html"


class AdminImportedFactsView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    template_name = "crm/imported_facts.html"
