"""
accounts/admin.py
-----------------
Admin per il modello Utente personalizzato.
Estende UserAdmin per mantenere tutte le funzionalità native di Django.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import Utente


@admin.register(Utente)
class UtenteAdmin(UserAdmin):
    list_display  = ("email", "first_name", "last_name", "numero", "avatar_preview", "is_staff", "is_active", "date_joined")
    list_filter   = ("is_staff", "is_active", "date_joined")
    search_fields = ("email", "first_name", "last_name", "numero")
    ordering      = ("last_name", "first_name")

    # Campi nella vista dettaglio
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Informazioni personali", {"fields": ("first_name", "last_name", "numero", "avatar")}),
        ("Permessi", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Date", {"fields": ("last_login", "date_joined")}),
    )
    # Campi nel form di creazione
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "first_name", "last_name", "numero", "password1", "password2"),
        }),
    )

    def avatar_preview(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" width="32" height="32" style="border-radius:50%;object-fit:cover;">',
                obj.avatar.url,
            )
        return format_html(
            '<span style="display:inline-flex;align-items:center;justify-content:center;'
            'width:32px;height:32px;border-radius:50%;background:#6c757d;color:#fff;font-size:12px;">{}</span>',
            obj.iniziali,
        )
    avatar_preview.short_description = "Avatar"
