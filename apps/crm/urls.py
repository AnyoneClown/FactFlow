from django.urls import path

from . import views

app_name = "crm"

urlpatterns = [
    path("", views.user_dashboard, name="user_dashboard"),
    path("upload/", views.upload, name="upload"),
    path("statistics/", views.statistics, name="statistics"),
    path("admin/", views.admin_dashboard, name="admin_dashboard"),
    path("admin/uploads/", views.admin_upload_logs, name="admin_upload_logs"),
    path("admin/users/", views.admin_users, name="admin_users"),
    path("admin/facts/", views.admin_imported_facts, name="admin_imported_facts"),
]
