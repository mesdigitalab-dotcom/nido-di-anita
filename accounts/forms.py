"""
accounts/forms.py
-----------------
Form riutilizzabili per registrazione, login, modifica profilo e cambio password.
"""

from django import forms
from django.contrib.auth.forms import (
    UserCreationForm,
    PasswordChangeForm,
)
from django.contrib.auth import get_user_model, authenticate
from django.core.exceptions import ValidationError

User = get_user_model()


class LoginForm(forms.Form):
    """
    Form di login che accetta username o email.
    Supporta anche l'accesso admin (is_staff).
    """

    username = forms.CharField(
        label="Username o Email",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Username o Email",
            "autofocus": True,
            "autocomplete": "username",
        }),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Password",
            "autocomplete": "current-password",
        }),
    )

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self._user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        login_input = self.cleaned_data.get("username", "").strip()
        password = self.cleaned_data.get("password", "")

        if not login_input or not password:
            return self.cleaned_data

        # Cerca l'utente per email o per username (case-insensitive)
        db_user = None
        if "@" in login_input:
            try:
                db_user = User.objects.get(email__iexact=login_input)
            except User.DoesNotExist:
                pass
        else:
            try:
                db_user = User.objects.get(username__iexact=login_input)
            except User.DoesNotExist:
                pass

        # authenticate() usa USERNAME_FIELD (email); passiamo sempre l'email
        user = None
        if db_user is not None:
            user = authenticate(self.request, username=db_user.email, password=password)

        if user is None:
            raise ValidationError("Username/email o password non corretti.")

        if not user.is_active:
            raise ValidationError("Questo account è disattivato.")

        self._user_cache = user
        return self.cleaned_data

    def get_user(self):
        return self._user_cache


class RegistrazioneForm(UserCreationForm):
    """Form di registrazione con campi aggiuntivi (nome, numero)."""

    first_name = forms.CharField(
        label="Nome",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Nome"}),
    )
    last_name = forms.CharField(
        label="Cognome",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Cognome"}),
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email"}),
    )
    numero = forms.CharField(
        label="Telefono",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "+39 333 1234567",
        }),
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Password"}),
    )
    password2 = forms.CharField(
        label="Conferma password",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Ripeti la password"}),
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "numero", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"].split("@")[0]
        user.numero = self.cleaned_data.get("numero", "")
        if commit:
            user.save()
        return user


class ProfiloForm(forms.ModelForm):
    """Form per la modifica del profilo utente."""

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "numero", "avatar")
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name":  forms.TextInput(attrs={"class": "form-control"}),
            "email":      forms.EmailInput(attrs={"class": "form-control"}),
            "numero":     forms.TextInput(attrs={"class": "form-control", "placeholder": "+39 333 1234567"}),
            "avatar":     forms.ClearableFileInput(attrs={"class": "form-control"}),
        }
        labels = {
            "first_name": "Nome",
            "last_name":  "Cognome",
            "email":      "Email",
            "numero":     "Telefono",
            "avatar":     "Foto profilo",
        }


class CambioPasswordForm(PasswordChangeForm):
    """Form cambio password con stile Bootstrap."""

    old_password = forms.CharField(
        label="Password attuale",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    new_password1 = forms.CharField(
        label="Nuova password",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    new_password2 = forms.CharField(
        label="Conferma nuova password",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )