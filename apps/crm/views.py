from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from .roles import AdminRequiredMixin


class UserDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "crm/user_dashboard.html"


class UploadView(LoginRequiredMixin, TemplateView):
    template_name = "crm/upload.html"


class StatisticsView(LoginRequiredMixin, TemplateView):
    template_name = "crm/statistics.html"


class AdminDashboardView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    template_name = "crm/dashboard.html"


class AdminUploadLogsView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    template_name = "crm/upload_logs.html"


class AdminUsersView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    template_name = "crm/users.html"


class AdminImportedFactsView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    template_name = "crm/imported_facts.html"
