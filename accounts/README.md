# `accounts` — App Django riutilizzabile per l'autenticazione

App plug-and-play che sostituisce il `User` di Django con un modello personalizzato
che usa l'**email come login** e aggiunge **numero di telefono** e **avatar**.

---

## Installazione in qualsiasi progetto Django

### 1. Copia la cartella `accounts/` nella root del tuo progetto

```
myproject/
├── accounts/        ← questa cartella
├── myapp/
├── myproject/
└── manage.py
```

### 2. `settings.py`

```python
INSTALLED_APPS = [
    # ... app Django di base ...
    'accounts',
    # ... le tue app ...
]

# OBBLIGATORIO — va impostato PRIMA della prima migrate
AUTH_USER_MODEL = 'accounts.Utente'

# Redirect di login/logout
LOGIN_URL          = 'accounts:login'
LOGIN_REDIRECT_URL = 'accounts:profilo'   # o un'altra url del tuo progetto
LOGOUT_REDIRECT_URL = '/'
```

### 3. `urls.py` (progetto)

```python
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('account/', include('accounts.urls', namespace='accounts')),
    # ... le tue url ...
]
```

### 4. Migrations

```bash
python manage.py makemigrations accounts
python manage.py migrate
python manage.py createsuperuser
```

---

## URL disponibili

| URL | Nome | Descrizione |
|-----|------|-------------|
| `/account/login/` | `accounts:login` | Login via email |
| `/account/logout/` | `accounts:logout` | Logout |
| `/account/registrazione/` | `accounts:registrazione` | Registrazione |
| `/account/profilo/` | `accounts:profilo` | Profilo utente |
| `/account/profilo/modifica/` | `accounts:modifica_profilo` | Modifica profilo |
| `/account/password/` | `accounts:cambio_password` | Cambio password |

---

## Navbar — tag templatetag

Nei tuoi template aggiungi il dropdown Account con un solo tag:

```html
{% load accounts_tags %}

<ul class="navbar-nav ms-auto">
    <!-- i tuoi link -->
    {% accounts_nav_items %}
</ul>
```

Mostra automaticamente:
- **Utente autenticato** → dropdown con avatar/iniziali, profilo, modifica, cambio password, logout
- **Non autenticato** → link Accedi + Registrati

> Richiede che `django.template.context_processors.request` sia nei `TEMPLATES` → `OPTIONS` → `context_processors` (è lì di default).

---

## Modello `Utente`

```python
from django.contrib.auth import get_user_model
User = get_user_model()

# Campi aggiuntivi rispetto al User standard:
# - email        (EmailField, unique, usato come USERNAME_FIELD)
# - numero       (CharField, opzionale, es. "+39 333 1234567")
# - avatar       (ImageField, opzionale)

# Proprietà utili:
# - .nome_completo  → "Mario Rossi" o email
# - .iniziali       → "MR" (usate nell'avatar placeholder)
```

---

## Referenziare il modello utente nelle tue app

Usa sempre `settings.AUTH_USER_MODEL` nelle ForeignKey, non `Utente` direttamente:

```python
from django.conf import settings

class MioModello(models.Model):
    utente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
```

---

## Templates

I template estendono `base.html` (il tuo). Personalizzali liberamente in
`accounts/templates/accounts/`.

| File | Contenuto |
|------|-----------|
| `login.html` | Form di login |
| `registrazione.html` | Form di registrazione |
| `profilo.html` | Pagina profilo |
| `modifica_profilo.html` | Form modifica profilo |
| `cambio_password.html` | Form cambio password |
| `nav_items.html` | Partial navbar (usato dal templatetag) |

---

## Dipendenze

Nessuna dipendenza esterna oltre a Django. Il campo `numero` è un semplice
`CharField` per massima portabilità. Se preferisci validazione avanzata installa
`django-phonenumber-field` e sostituisci il campo in `models.py`.
