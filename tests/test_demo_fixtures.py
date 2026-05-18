import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command

from apps.imports.models import ImportedFact, UploadLog


@pytest.mark.django_db
def test_demo_fixture_loads_expected_website_data():
    call_command("loaddata", "demo_data", verbosity=0)

    User = get_user_model()

    assert Group.objects.filter(name="Admin").exists()
    assert Group.objects.filter(name="User").exists()
    assert User.objects.filter(email="admin@factflow.local").exists()
    assert User.objects.filter(email="analyst@factflow.local").exists()
    assert User.objects.filter(email="manager@factflow.local").exists()
    assert UploadLog.objects.count() >= 4
    assert ImportedFact.objects.count() >= 8


@pytest.mark.django_db
def test_demo_fixture_can_be_loaded_twice_without_creating_duplicates():
    call_command("loaddata", "demo_data", verbosity=0)
    call_command("loaddata", "demo_data", verbosity=0)

    User = get_user_model()

    assert User.objects.filter(email="admin@factflow.local").count() == 1
    assert UploadLog.objects.count() == 4
    assert ImportedFact.objects.count() == 8
