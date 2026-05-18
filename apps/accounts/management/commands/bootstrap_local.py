from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    help = "Load local demo data and ensure a Docker-friendly superuser exists."

    def handle(self, *args, **options):
        User = get_user_model()

        if not User.objects.filter(email="admin@factflow.local").exists():
            self.stdout.write("Loading demo fixture data...")
            call_command("loaddata", "demo_data", verbosity=0)
        else:
            self.stdout.write("Demo fixture data already present, skipping.")

        email = getattr(settings, "DJANGO_SUPERUSER_EMAIL", "") or "admin@example.com"
        password = getattr(settings, "DJANGO_SUPERUSER_PASSWORD", "") or "admin12345"

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            },
        )

        changed = False
        if not user.is_staff:
            user.is_staff = True
            changed = True
        if not user.is_superuser:
            user.is_superuser = True
            changed = True
        if not user.is_active:
            user.is_active = True
            changed = True
        if password and not user.check_password(password):
            user.set_password(password)
            changed = True

        if created or changed:
            user.save()
            self.stdout.write(f"Superuser ready: {email}")
        else:
            self.stdout.write(f"Superuser already up to date: {email}")
