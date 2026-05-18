"""Root URL configuration for FactFlow."""

from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path

from apps.accounts.forms import EmailAuthenticationForm

urlpatterns = [
    path(
        "login/",
        LoginView.as_view(
            template_name="registration/login.html",
            authentication_form=EmailAuthenticationForm,
        ),
        name="login",
    ),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("crm/", include("apps.crm.urls")),
    path("admin/", admin.site.urls),
]
