from django.core.management import call_command


def test_django_system_check_passes():
    call_command("check")
