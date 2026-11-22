from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

class Incident(models.Model):
    class Severity(models.TextChoices):
        LOW = "low", "Faible"
        MEDIUM = "medium", "Modérée"
        HIGH = "high", "Élevée"
        CRITICAL = "critical", "Critique"

    class Status(models.TextChoices):
        OPEN = "open", "Ouvert"
        TRIAGED = "triaged", "Qualifié"
        IN_PROGRESS = "in_progress", "En cours"
        RESOLVED = "resolved", "Résolu"
        CLOSED = "closed", "Clôturé"

    title = models.CharField(max_length=2000, blank=True)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="incidents")
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_incidents")
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.MEDIUM)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [
            models.Index(fields=["created_by", "-created_at"], name="incident_owner_created_idx"),
            models.Index(fields=["assigned_to", "-created_at"], name="incident_assigned_created_idx"),
        ]
        permissions = [
            ("view_all_incidents", "Can view all incidents"),
            ("view_assigned_incidents", "Can view assigned incidents"),
            ("assign_incident", "Can assign incidents to analysts"),
        ]

    @property
    def reference(self):
        return f"INC-{self.pk:04d}"

    def __str__(self):
        return f"{self.reference}: {self.title}"

    def clean(self):
        super().clean()
        if not self.pk:
            return
        previous_status = type(self).objects.filter(pk=self.pk).values_list("status", flat=True).first()
        if previous_status == self.status:
            return
        allowed = {
            self.Status.OPEN: {self.Status.TRIAGED, self.Status.IN_PROGRESS, self.Status.CLOSED},
            self.Status.TRIAGED: {self.Status.IN_PROGRESS, self.Status.CLOSED},
            self.Status.IN_PROGRESS: {self.Status.TRIAGED, self.Status.RESOLVED, self.Status.CLOSED},
            self.Status.RESOLVED: {self.Status.CLOSED},
            self.Status.CLOSED: set(),
        }
        if self.status not in allowed.get(previous_status, set()):
            raise ValidationError({"status": "Cette transition d’état n’est pas autorisée."})


class IncidentComment(models.Model):
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="incident_comments")
    body = models.TextField(max_length=10000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "pk"]

    def __str__(self):
        return f"Comment on {self.incident.reference} by {self.author}"


class IncidentAuditEvent(models.Model):
    class Action(models.TextChoices):
        CREATED = "created", "Created"
        UPDATED = "updated", "Updated"
        DELETED = "deleted", "Deleted"
        COMMENTED = "commented", "Commented"

    incident = models.ForeignKey(Incident, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_events")
    incident_reference = models.CharField(max_length=24)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="incident_audit_events")
    action = models.CharField(max_length=12, choices=Action.choices)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]

    def __str__(self):
        return f"{self.incident_reference}: {self.action} by {self.actor}"
