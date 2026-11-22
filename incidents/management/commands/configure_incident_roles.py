from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError


ROLE_PERMISSIONS = {
    "Incident reporters": (),
    "Incident analysts": (
        "view_incident",
        "view_assigned_incidents",
        "change_incident",
        "view_incidentcomment",
        "add_incidentcomment",
    ),
    "Incident administrators": (
        "add_incident",
        "change_incident",
        "delete_incident",
        "view_incident",
        "view_all_incidents",
        "view_assigned_incidents",
        "assign_incident",
        "view_incidentcomment",
        "view_incidentauditevent",
    ),
}


class Command(BaseCommand):
    help = "Create the Incident Desk role groups and optionally assign existing users."

    def add_arguments(self, parser):
        parser.add_argument("--reporter-username")
        parser.add_argument("--analyst-username")
        parser.add_argument("--admin-username")

    def handle(self, *args, **options):
        groups = {}
        for group_name, codenames in ROLE_PERMISSIONS.items():
            group, _ = Group.objects.get_or_create(name=group_name)
            permissions = Permission.objects.filter(content_type__app_label="incidents", codename__in=codenames)
            if permissions.count() != len(codenames):
                missing = sorted(set(codenames) - set(permissions.values_list("codename", flat=True)))
                raise CommandError(f"Migrate the database first; permissions are missing: {', '.join(missing)}")
            group.permissions.set(permissions)
            groups[group_name] = group

        user_model = get_user_model()
        assignments = (
            (options["reporter_username"], "Incident reporters", False),
            (options["analyst_username"], "Incident analysts", False),
            (options["admin_username"], "Incident administrators", True),
        )
        for username, group_name, staff in assignments:
            if not username:
                continue
            try:
                user = user_model.objects.get(**{user_model.USERNAME_FIELD: username})
            except user_model.DoesNotExist as exc:
                raise CommandError(f"User {username!r} does not exist. Create the account first.") from exc
            user.groups.add(groups[group_name])
            if group_name == "Incident reporters":
                user.groups.remove(groups["Incident analysts"], groups["Incident administrators"])
                user.is_staff = False
                user.is_superuser = False
            elif group_name == "Incident analysts":
                user.groups.remove(groups["Incident reporters"], groups["Incident administrators"])
                user.is_staff = False
                user.is_superuser = False
            else:
                user.groups.remove(groups["Incident reporters"], groups["Incident analysts"])
                user.is_staff = staff
                user.is_superuser = False
            user.save(update_fields=["is_staff", "is_superuser"])
        self.stdout.write(self.style.SUCCESS("Incident roles are configured."))
