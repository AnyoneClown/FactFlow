from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .roles import admin_required


@login_required
def user_dashboard(request):
    return render(request, "crm/user_dashboard.html")


@login_required
def upload(request):
    return render(request, "crm/upload.html")


@login_required
def statistics(request):
    return render(request, "crm/statistics.html")


@login_required
@admin_required
def admin_dashboard(request):
    return render(request, "crm/dashboard.html")


@login_required
@admin_required
def admin_upload_logs(request):
    return render(request, "crm/upload_logs.html")


@login_required
@admin_required
def admin_users(request):
    return render(request, "crm/users.html")


@login_required
@admin_required
def admin_imported_facts(request):
    return render(request, "crm/imported_facts.html")
