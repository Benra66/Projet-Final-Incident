import os

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Create or update the two course accounts using passwords supplied only through environment variables."

    @transaction.atomic
    def handle(self, *args, **options):
        reporter_password = os.getenv("INCIDENT_REPORTER_PASSWORD", "")
        admin_password = os.getenv("INCIDENT_ADMIN_PASSWORD", "")
        if not reporter_password or not admin_password:
            raise CommandError("Set INCIDENT_REPORTER_PASSWORD and INCIDENT_ADMIN_PASSWORD in the private environment.")
        call_command("configure_incident_roles")

        User = get_user_model()
        reporter, _ = User.objects.get_or_create(username="Nazairefabsimple")
        reporter.set_password(reporter_password)
        reporter.is_active = True
        reporter.is_staff = False
        reporter.is_superuser = False
        reporter.save()

        admin_user, _ = User.objects.get_or_create(username="Nazairefabadmin")
        admin_user.set_password(admin_password)
        admin_user.is_active = True
        admin_user.is_staff = True
        admin_user.is_superuser = False
        admin_user.save()

        reporter.groups.set([Group.objects.get(name="Incident reporters")])
        admin_user.groups.set([Group.objects.get(name="Incident administrators")])
        self.stdout.write(self.style.SUCCESS("Course accounts and least-privilege roles are configured."))
