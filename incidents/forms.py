from django import forms
from .models import Incident

class IncidentForm(forms.ModelForm):
    class Meta:
        model = Incident
        # Ownership is never accepted from the browser.
        fields = ["title", "description"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Un titre court et descriptif", "autofocus": True}),
            "description": forms.Textarea(attrs={"rows": 8, "placeholder": "Que s'est-il passé ?"}),
        }
        help_texts = {
            "title": "",
            "description": "Utilisez du texte brut ; n'entrez pas de mots de passe ni de données personnelles.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Supprimer toutes les validations de longueur minimale
        self.fields["title"].min_length = None
        self.fields["description"].min_length = None
        self.fields["title"].required = False
        self.fields["description"].required = False
        # Vider les validateurs hérités du modèle
        self.fields["title"].validators = []
        self.fields["description"].validators = []
