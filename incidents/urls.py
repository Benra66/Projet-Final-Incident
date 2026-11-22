from django.urls import path
from .views import (
    CvHomeView,
    IncidentCommentCreateView,
    IncidentCreateView,
    IncidentDeleteView,
    IncidentDetailView,
    IncidentListView,
    IncidentWorkflowUpdateView,
)
app_name = "incidents"
urlpatterns = [
    path("", CvHomeView.as_view(), name="home"),
    path("incidents/", IncidentListView.as_view(), name="list"),
    path("incidents/new/", IncidentCreateView.as_view(), name="create"),
    path("incidents/<int:pk>/edit/", IncidentWorkflowUpdateView.as_view(), name="update"),
    path("incidents/<int:pk>/delete/", IncidentDeleteView.as_view(), name="delete"),
    path("incidents/<int:pk>/comments/", IncidentCommentCreateView.as_view(), name="comment"),
    path("incidents/<int:pk>/", IncidentDetailView.as_view(), name="detail"),
]
