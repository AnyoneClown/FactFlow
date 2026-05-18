"""Root URL configuration for FactFlow."""

from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("health", lambda request: JsonResponse({"status": "ok"})),
    path("users/", include("apps.accounts.urls")),
    path("django-admin/", admin.site.urls),
    path("crm/", RedirectView.as_view(pattern_name="crm:user_dashboard", permanent=False)),
    path("", include("apps.crm.urls")),
]
