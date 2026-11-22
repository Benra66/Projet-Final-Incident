from django.conf import settings
from django.core.validators import MinLengthValidator
from django.db import models

class Incident(models.Model):
    title = models.CharField(max_length=2000, blank=True)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="incidents")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [models.Index(fields=["created_by", "-created_at"], name="incident_owner_created_idx")]

    @property
    def reference(self):
        return f"INC-{self.pk:04d}"

    def __str__(self):
        return f"{self.reference}: {self.title}"
