from django.contrib import admin
from .models import Incident, IncidentAuditEvent, IncidentComment

@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ["reference", "title", "severity", "status", "assigned_to", "created_by", "created_at"]
    list_filter = ["severity", "status", "created_at"]
    list_select_related = ["created_by", "assigned_to"]
    search_fields = ["title", "created_by__username", "assigned_to__username"]
    readonly_fields = ["created_by", "created_at"]
    autocomplete_fields = ["assigned_to"]
    list_per_page = 50

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
        IncidentAuditEvent.objects.create(
            incident=obj,
            incident_reference=obj.reference,
            actor=request.user,
            action=IncidentAuditEvent.Action.UPDATED if change else IncidentAuditEvent.Action.CREATED,
            metadata={"changed_fields": list(form.changed_data)} if change else {},
        )

    def delete_model(self, request, obj):
        IncidentAuditEvent.objects.create(
            incident=obj,
            incident_reference=obj.reference,
            actor=request.user,
            action=IncidentAuditEvent.Action.DELETED,
        )
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for obj in queryset.select_related("created_by"):
            IncidentAuditEvent.objects.create(
                incident=obj,
                incident_reference=obj.reference,
                actor=request.user,
                action=IncidentAuditEvent.Action.DELETED,
            )
        super().delete_queryset(request, queryset)


@admin.register(IncidentComment)
class IncidentCommentAdmin(admin.ModelAdmin):
    list_display = ["incident", "author", "created_at"]
    list_select_related = ["incident", "author"]
    search_fields = ["incident__title", "author__username", "body"]
    readonly_fields = ["incident", "author", "body", "created_at"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(IncidentAuditEvent)
class IncidentAuditEventAdmin(admin.ModelAdmin):
    list_display = ["incident_reference", "action", "actor", "created_at"]
    list_filter = ["action", "created_at"]
    search_fields = ["incident_reference", "actor__username"]
    readonly_fields = ["incident", "incident_reference", "actor", "action", "metadata", "created_at"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
