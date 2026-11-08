"""Teams Forms"""
from django import forms
from .models import Team, TeamInvite
from players.models import Player


class TeamCreateForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ['name', 'tag', 'game', 'description', 'logo', 'is_recruiting']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control cyber-input', 'placeholder': 'Team Name'}),
            'tag': forms.TextInput(attrs={'class': 'form-control cyber-input', 'placeholder': 'VZG'}),
            'game': forms.Select(attrs={'class': 'form-select cyber-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control cyber-input', 'rows': 3}),
            'logo': forms.FileInput(attrs={'class': 'form-control cyber-input'}),
            'is_recruiting': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class TeamInviteForm(forms.ModelForm):
    invited_player = forms.ModelChoiceField(
        queryset=Player.objects.filter(is_available=True),
        widget=forms.Select(attrs={'class': 'form-select cyber-select'})
    )

    class Meta:
        model = TeamInvite
        fields = ['invited_player', 'role', 'message']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select cyber-select'}),
            'message': forms.Textarea(attrs={'class': 'form-control cyber-input', 'rows': 2}),
        }
