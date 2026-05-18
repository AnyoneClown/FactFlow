"""Root URL configuration for FactFlow."""

from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

urlpatterns = [
    path("health", lambda request: JsonResponse({"status": "ok"})),
    path("users/", include("apps.accounts.urls")),
    path("crm/", include("apps.crm.urls")),
    path("admin/", admin.site.urls),
]
