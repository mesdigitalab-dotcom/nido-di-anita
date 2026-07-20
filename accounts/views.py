"""
accounts/views.py
-----------------
Views per registrazione, login, logout, profilo e cambio password.
Tutte compatibili con qualsiasi progetto Django.

Configurazione in settings.py:
  LOGIN_URL          = 'accounts:login'
  LOGIN_REDIRECT_URL = 'accounts:profilo'   # o qualsiasi url
  LOGOUT_REDIRECT_URL = '/'                 # o qualsiasi url
"""

from django.shortcuts import render, redirect
from django.contrib.auth import (
    login, logout, authenticate,
    update_session_auth_hash,
)
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import LoginForm, RegistrazioneForm, ProfiloForm, CambioPasswordForm


# ── Login ──────────────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:profilo")

    form = LoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        next_url = request.GET.get("next") or "accounts:profilo"
        return redirect(next_url)

    return render(request, "accounts/login.html", {"form": form})


# ── Logout ─────────────────────────────────────────────────────────────────────

def logout_view(request):
    logout(request)
    return redirect("/")


# ── Registrazione ──────────────────────────────────────────────────────────────

def registrazione_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:profilo")

    form = RegistrazioneForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f"Benvenuto, {user.first_name or user.email}!")
        return redirect("accounts:profilo")

    return render(request, "accounts/registrazione.html", {"form": form})


# ── Profilo ────────────────────────────────────────────────────────────────────

@login_required
def profilo_view(request):
    return render(request, "accounts/profilo.html", {"utente": request.user})


@login_required
def modifica_profilo_view(request):
    form = ProfiloForm(
        request.POST or None,
        request.FILES or None,
        instance=request.user,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profilo aggiornato con successo.")
        return redirect("accounts:profilo")

    return render(request, "accounts/modifica_profilo.html", {"form": form})


# ── Cambio password ────────────────────────────────────────────────────────────

@login_required
def cambio_password_view(request):
    form = CambioPasswordForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)  # mantiene la sessione attiva
        messages.success(request, "Password aggiornata con successo.")
        return redirect("accounts:profilo")

    return render(request, "accounts/cambio_password.html", {"form": form})
