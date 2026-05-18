"""Root URL configuration for FactFlow."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("users/", include("apps.accounts.urls")),
    path("crm/", include("apps.crm.urls")),
    path("admin/", admin.site.urls),
]
