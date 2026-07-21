"""
Django settings for django_project project.
Configurazione basata su variabili d'ambiente, pronta per produzione/Docker.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Carica un file .env locale se presente (in produzione le variabili arrivano
# dall'ambiente/dal servizio di hosting, il file .env non serve e non va committato).
load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def env_list(name, default=""):
    return [v.strip() for v in os.environ.get(name, default).split(",") if v.strip()]


# ── Sicurezza di base ───────────────────────────────────────────────────────

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]  # obbligatoria: l'app non parte senza

DEBUG = env_bool("DJANGO_DEBUG", default=False)

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

CSRF_TRUSTED_ORIGINS = env_list(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000",
)

# ── App ──────────────────────────────────────────────────────────────────────

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'app',
    'accounts',
    'storages',
    'anymail',
]

AUTH_USER_MODEL = 'accounts.Utente'

# Permette login con username O email, sia nel sito che nell'admin
AUTHENTICATION_BACKENDS = [
    'accounts.backends.UsernameOrEmailBackend',
]

LOGIN_URL          = 'accounts:login'
LOGIN_REDIRECT_URL = 'accounts:profilo'
LOGOUT_REDIRECT_URL = '/'

# ── Middleware ───────────────────────────────────────────────────────────────

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ── Templates ────────────────────────────────────────────────────────────────

ROOT_URLCONF = 'django_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'django_project.wsgi.application'

# ── Database ─────────────────────────────────────────────────────────────────
# Tutte le credenziali arrivano da variabili d'ambiente: nessun segreto nel codice.

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ["DB_NAME"],
        'USER': os.environ["DB_USER"],
        'PASSWORD': os.environ["DB_PASSWORD"],
        'HOST': os.environ["DB_HOST"],
        'PORT': os.environ.get("DB_PORT", "5432"),
        'OPTIONS': {
            'sslmode': os.environ.get("DB_SSLMODE", "require"),
        },
        'CONN_MAX_AGE': 60,
    }
}

# ── Password validation ───────────────────────────────────────────────────────

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Internazionalizzazione ────────────────────────────────────────────────────

LANGUAGE_CODE = 'it'
TIME_ZONE     = 'Europe/Rome'
USE_I18N      = True
USE_TZ        = True

# ── File statici e media ──────────────────────────────────────────────────────

STATIC_URL  = '/static/'
STATIC_ROOT = BASE_DIR / "staticfiles"          # destinazione di collectstatic
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []

# ── Media (upload utenti/admin: galleria, avatar) ─────────────────────────────
# Il filesystem dei container su Render (e host simili) NON è persistente: ad ogni
# deploy/riavvio i file caricati andrebbero persi. Per questo i media vengono
# salvati su uno storage S3-compatibile esterno (Cloudflare R2, gratuito fino a
# 10GB e senza costi di banda in uscita) quando le variabili R2_* sono presenti.
# In locale, se non configuri R2, si usa il filesystem come prima (comodo per lo
# sviluppo, senza dover creare un bucket per ogni prova).

R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "")

if R2_BUCKET_NAME:
    AWS_ACCESS_KEY_ID = os.environ["R2_ACCESS_KEY_ID"]
    AWS_SECRET_ACCESS_KEY = os.environ["R2_SECRET_ACCESS_KEY"]
    AWS_STORAGE_BUCKET_NAME = R2_BUCKET_NAME
    AWS_S3_ENDPOINT_URL = os.environ["R2_ENDPOINT_URL"]  # es. https://<account_id>.r2.cloudflarestorage.com
    AWS_S3_ADDRESSING_STYLE = "virtual"
    AWS_S3_SIGNATURE_VERSION = "s3v4"
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None  # R2 non supporta le ACL stile S3
    AWS_QUERYSTRING_AUTH = False  # URL pubblici puliti, senza firma/scadenza

    # Dominio pubblico da cui servire i file: o il dominio pubblico "r2.dev" del
    # bucket, o un dominio custom collegato al bucket su Cloudflare.
    R2_PUBLIC_DOMAIN = os.environ.get("R2_PUBLIC_DOMAIN", "")
    if R2_PUBLIC_DOMAIN:
        AWS_S3_CUSTOM_DOMAIN = R2_PUBLIC_DOMAIN

    STORAGES = {
        "default": {"BACKEND": "storages.backends.s3.S3Storage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }
else:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }

MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'  # usato solo quando R2 non è configurato

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Email ──────────────────────────────────────────────────────────────────────
# Render (piano free) blocca le connessioni SMTP in uscita: usiamo un backend
# HTTP (Anymail + Resend) invece di django.core.mail.backends.smtp.
# Sia la API key che il mittente arrivano da variabili d'ambiente: nessun
# segreto e nessun indirizzo hardcoded nel codice.

EMAIL_BACKEND = "anymail.backends.resend.EmailBackend"

ANYMAIL = {
    "RESEND_API_KEY": os.environ["RESEND_API_KEY"],  # obbligatoria: l'app non parte senza
}

DEFAULT_FROM_EMAIL = os.environ["DEFAULT_FROM_EMAIL"]  # es. notifiche@tuodominio.it


# ── iCal ───────────────────────────────────────────────────────────────────────

ICAL_PERSONAL_PATH = str(BASE_DIR / "ics" / "calendario.ics")
ICAL_CACHE_DIR      = str(BASE_DIR / "ics" / "cache")
ICAL_EXTERNAL_URLS  = env_list("ICAL_EXTERNAL_URLS", "")

# ── Sicurezza in produzione (attiva quando DEBUG=False) ──────────────────────

if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 7  # 7 giorni, poi aumentabile
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    # Molti host (Render, Railway, Fly.io, ecc.) mettono un proxy TLS davanti all'app
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ── Logging (utile per capire cosa succede quando gira in un container) ──────

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
    },
}
