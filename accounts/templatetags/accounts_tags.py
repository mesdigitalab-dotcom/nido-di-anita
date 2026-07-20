"""
accounts/templatetags/accounts_tags.py
---------------------------------------
Tag riutilizzabili per la navbar.

Uso nel template:
    {% load accounts_tags %}
    {% accounts_nav_items %}
"""

from django import template
from django.urls import reverse

register = template.Library()


@register.inclusion_tag("accounts/nav_items.html", takes_context=True)
def accounts_nav_items(context):
    """
    Renderizza i link di Account da inserire nella navbar.
    Mostra link diversi per utenti autenticati e non.
    """
    request = context.get("request")
    return {"user": request.user if request else None}
