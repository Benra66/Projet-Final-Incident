import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from incidents.models import Incident


class Command(BaseCommand):
    help = "Seed one disposable reporter and synthetic incident for local DAST."

    def handle(self, *args, **options):
        if settings.SETTINGS_MODULE != "config.settings.dast":
            raise CommandError("This command only runs with config.settings.dast.")
        password = os.getenv("DAST_REPORTER_PASSWORD", "")
        if not password:
            raise CommandError("Set DAST_REPORTER_PASSWORD in the temporary DAST environment.")
        User = get_user_model()
        reporter, _ = User.objects.get_or_create(username="zap-reporter")
        reporter.set_password(password)
        reporter.is_active = True
        reporter.is_staff = False
        reporter.is_superuser = False
        reporter.save()
        Incident.objects.get_or_create(
            created_by=reporter,
            title="Synthetic ZAP scan record",
            defaults={"description": "Disposable test data used by the local authenticated security scan."},
        )
        self.stdout.write(self.style.SUCCESS("Disposable DAST account and incident are ready."))
