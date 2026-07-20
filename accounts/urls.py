"""
accounts/urls.py
----------------
Include questo nel tuo progetto con:

    path('account/', include('accounts.urls', namespace='accounts')),

e aggiungi in settings.py:
    LOGIN_URL          = 'accounts:login'
    LOGIN_REDIRECT_URL = 'accounts:profilo'
    LOGOUT_REDIRECT_URL = '/'
"""

from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("login/",            views.login_view,           name="login"),
    path("logout/",           views.logout_view,          name="logout"),
    path("registrazione/",    views.registrazione_view,   name="registrazione"),
    path("profilo/",          views.profilo_view,         name="profilo"),
    path("profilo/modifica/", views.modifica_profilo_view, name="modifica_profilo"),
    path("password/",         views.cambio_password_view, name="cambio_password"),
]
