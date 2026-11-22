from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from .models import Incident, IncidentComment

class IncidentForm(forms.ModelForm):
    title = forms.CharField(
        required=False,
        max_length=2000,
        widget=forms.TextInput(attrs={"placeholder": "Un titre court et descriptif", "autofocus": True}),
    )
    description = forms.CharField(
        required=False,
        max_length=5000,
        widget=forms.Textarea(attrs={"rows": 8, "placeholder": "Que s'est-il passé ?"}),
        help_text="Utilisez du texte brut ; n'entrez pas de mots de passe ni de données personnelles.",
    )

    class Meta:
        model = Incident
        # Ownership is never accepted from the browser.
        fields = ["title", "description"]
        help_texts = {"title": ""}


class IncidentWorkflowForm(forms.ModelForm):
    class Meta:
        model = Incident
        fields = ["status", "severity", "assigned_to"]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if not (user and user.has_perm("incidents.assign_incident")):
            self.fields.pop("assigned_to")
        else:
            User = get_user_model()
            analyst_group = Group.objects.filter(name="Incident analysts").first()
            self.fields["assigned_to"].queryset = (
                User.objects.filter(groups=analyst_group, is_active=True).order_by(User.USERNAME_FIELD)
                if analyst_group else User.objects.none()
            )


class IncidentCommentForm(forms.ModelForm):
    class Meta:
        model = IncidentComment
        fields = ["body"]
        widgets = {"body": forms.Textarea(attrs={"rows": 4, "maxlength": 10000})}
