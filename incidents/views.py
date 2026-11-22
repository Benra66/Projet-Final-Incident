from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView, TemplateView

from .forms import IncidentCommentForm, IncidentForm, IncidentWorkflowForm
from .models import Incident, IncidentAuditEvent


def accessible_incidents(user):
    incidents = Incident.objects.select_related("created_by", "assigned_to")
    if user.has_perm("incidents.view_all_incidents"):
        return incidents
    if user.has_perm("incidents.view_assigned_incidents"):
        return incidents.filter(Q(created_by=user) | Q(assigned_to=user))
    return incidents.filter(created_by=user)


class IncidentAccessMixin(LoginRequiredMixin):
    def get_queryset(self):
        return accessible_incidents(self.request.user)


class IncidentListView(IncidentAccessMixin, ListView):
    model = Incident
    template_name = "incidents/list.html"
    context_object_name = "incidents"
    paginate_by = 10


class IncidentDetailView(IncidentAccessMixin, DetailView):
    model = Incident
    template_name = "incidents/detail.html"
    context_object_name = "incident"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["comment_form"] = IncidentCommentForm()
        return context


class IncidentCreateView(LoginRequiredMixin, CreateView):
    model = Incident
    form_class = IncidentForm
    template_name = "incidents/form.html"

    @transaction.atomic
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        IncidentAuditEvent.objects.create(
            incident=self.object,
            incident_reference=self.object.reference,
            actor=self.request.user,
            action=IncidentAuditEvent.Action.CREATED,
        )
        messages.success(self.request, "Incident créé.")
        return response

    def get_success_url(self):
        return reverse("incidents:detail", kwargs={"pk": self.object.pk})


class IncidentWorkflowUpdateView(IncidentAccessMixin, PermissionRequiredMixin, UpdateView):
    model = Incident
    form_class = IncidentWorkflowForm
    template_name = "incidents/workflow_form.html"
    permission_required = "incidents.change_incident"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    @transaction.atomic
    def form_valid(self, form):
        changed_fields = form.changed_data
        response = super().form_valid(form)
        IncidentAuditEvent.objects.create(
            incident=self.object,
            incident_reference=self.object.reference,
            actor=self.request.user,
            action=IncidentAuditEvent.Action.UPDATED,
            metadata={"changed_fields": changed_fields},
        )
        messages.success(self.request, "Suivi de l’incident mis à jour.")
        return response

    def get_success_url(self):
        return reverse("incidents:detail", kwargs={"pk": self.object.pk})


class IncidentDeleteView(IncidentAccessMixin, PermissionRequiredMixin, DeleteView):
    model = Incident
    template_name = "incidents/confirm_delete.html"
    permission_required = "incidents.delete_incident"
    success_url = reverse_lazy("incidents:list")

    @transaction.atomic
    def form_valid(self, form):
        IncidentAuditEvent.objects.create(
            incident=self.object,
            incident_reference=self.object.reference,
            actor=self.request.user,
            action=IncidentAuditEvent.Action.DELETED,
        )
        messages.success(self.request, "Incident supprimé.")
        return super().form_valid(form)


class IncidentCommentCreateView(LoginRequiredMixin, View):
    @transaction.atomic
    def post(self, request, pk):
        incident = get_object_or_404(accessible_incidents(request.user), pk=pk)
        form = IncidentCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.incident = incident
            comment.author = request.user
            comment.save()
            IncidentAuditEvent.objects.create(
                incident=incident,
                incident_reference=incident.reference,
                actor=request.user,
                action=IncidentAuditEvent.Action.COMMENTED,
                metadata={"comment_id": comment.pk},
            )
            messages.success(request, "Commentaire ajouté.")
        else:
            messages.error(request, "Le commentaire doit contenir au plus 10 000 caractères.")
        return redirect("incidents:detail", pk=incident.pk)

    def http_method_not_allowed(self, request, *args, **kwargs):
        return HttpResponseNotAllowed(["POST"])


class CvHomeView(TemplateView):
    template_name = "pages/cv.html"
