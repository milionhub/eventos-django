"""Settings shared by every environment. Values that change per machine come from `.env`."""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
REPO_DIR = BASE_DIR.parent

env = environ.Env()
# The `.env` file lives at the repository root (shared with compose.yaml).
# Real environment variables always take precedence over the file.
environ.Env.read_env(REPO_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]
THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
]
LOCAL_APPS = [
    "apps.core",
    "apps.accounts",
    "apps.organizations",
    "apps.events",
    "apps.ticketing",
    "apps.checkin",
]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["ATOMIC_REQUESTS"] = False  # transactions are explicit in services
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-es"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # The only client is the Angular SPA: JSON in, JSON out.
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "apps.core.exceptions.exception_handler",
    # Opt-in per view with `throttle_scope` (RNF-05).
    "DEFAULT_THROTTLE_RATES": {
        "login": env("THROTTLE_LOGIN_RATE", default="10/min"),
        "reservations": env("THROTTLE_RESERVATIONS_RATE", default="20/min"),
    },
}

# ADR-0003: short-lived access token in memory (Angular), refresh token in an httpOnly cookie.
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
}
REFRESH_COOKIE = {
    "key": "refresh_token",
    "path": "/api/v1/auth/",  # only sent to the auth endpoints
    "httponly": True,
    "samesite": "Strict",
    "secure": env.bool("REFRESH_COOKIE_SECURE", default=not DEBUG),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "eventos-django API",
    "DESCRIPTION": "Gestión de eventos, reservas y entradas QR.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": r"/api/v1",
    "COMPONENT_SPLIT_REQUEST": True,
    # Explicit names: several models have a "status", and generic names would collide.
    "ENUM_NAME_OVERRIDES": {
        "EventStatusEnum": "apps.events.models.Event.Status",
        "RoleEnum": "apps.organizations.models.Membership.Role",
        "ReservationStatusEnum": "apps.ticketing.models.Reservation.Status",
        "TicketStatusEnum": "apps.ticketing.models.Ticket.Status",
    },
}
