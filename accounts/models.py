"""
accounts/models.py
------------------
Modello utente personalizzato riutilizzabile in qualsiasi progetto Django.

Aggiunge al User di base:
  - email come USERNAME_FIELD (login via email)
  - numero di telefono (via django-phonenumber-field)
  - avatar opzionale

Installazione rapida:
  1. Aggiungi 'accounts' a INSTALLED_APPS
  2. Imposta AUTH_USER_MODEL = 'accounts.Utente'
  3. python manage.py makemigrations && migrate
"""

from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager


class UtenteManager(BaseUserManager):
    """Manager che usa l'email come identificatore univoco."""

    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("L'email è obbligatoria.")
        email = self.normalize_email(email)
        extra.setdefault("username", email.split("@")[0])
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra)


class Utente(AbstractUser):
    """
    Utente personalizzato.
    Sostituisce il modello User standard di Django.
    """

    email = models.EmailField(unique=True, verbose_name="Email")
    numero = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Numero di telefono",
        help_text="Formato internazionale es. +39 333 1234567",
    )
    avatar = models.ImageField(
        upload_to="accounts/avatars/",
        blank=True,
        null=True,
        verbose_name="Foto profilo",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UtenteManager()

    class Meta:
        verbose_name = "Utente"
        verbose_name_plural = "Utenti"
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return self.get_full_name() or self.email

    @property
    def nome_completo(self):
        return self.get_full_name() or self.email

    @property
    def iniziali(self):
        parts = [self.first_name, self.last_name]
        return "".join(p[0].upper() for p in parts if p) or self.email[0].upper()
