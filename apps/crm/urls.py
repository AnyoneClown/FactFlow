from django.urls import path

from . import views

app_name = "crm"

urlpatterns = [
    path("", views.UserDashboardView.as_view(), name="user_dashboard"),
    path("upload/", views.UploadView.as_view(), name="upload"),
    path("statistics/", views.StatisticsView.as_view(), name="statistics"),
    path("admin/", views.AdminDashboardView.as_view(), name="admin_dashboard"),
    path(
        "admin/uploads/",
        views.AdminUploadLogsView.as_view(),
        name="admin_upload_logs",
    ),
    path("admin/users/", views.AdminUsersView.as_view(), name="admin_users"),
    path(
        "admin/facts/",
        views.AdminImportedFactsView.as_view(),
        name="admin_imported_facts",
    ),
]
