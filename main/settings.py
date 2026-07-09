# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Base settings for the Entirius Volkanos service — framework wiring only.

Environment configuration (ENVIRONMENT, SECRET_KEY, DATABASES, adopted modules)
lives in main/settings_local.py (gitignored) — REQUIRED, one per environment;
template: main/settings_example.py. The service refuses to boot without it.
"""

from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

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
    "drf_spectacular",
]

# Volkanos modules, adopted bottom-up stage by stage — override per environment in settings_local.
LOCAL_APPS: list[str] = []

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "main.urls"

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

WSGI_APPLICATION = "main.wsgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Entirius Volkanos Service API",
    "DESCRIPTION": "Base Volkanos service of the Entirius platform",
    "VERSION": "3.0.0a1",
    "SERVE_INCLUDE_SCHEMA": False,
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
TMP_DIR = BASE_DIR / "tmp"  # required by django_pim (file/picture processing)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Fail-closed: no settings_local.py means the environment was never consciously
# configured (no explicit env type, DB, secret key) — refuse to boot.
try:
    from .settings_local import *  # noqa: F403
except ModuleNotFoundError as exc:
    raise ImproperlyConfigured(
        "main/settings_local.py not found - every environment must provide its own. "
        "Copy main/settings_example.py and set ENVIRONMENT, SECRET_KEY, DATABASES."
    ) from exc

_missing = [name for name in ("ENVIRONMENT", "SECRET_KEY", "DATABASES") if name not in globals()]
if _missing:
    raise ImproperlyConfigured(f"main/settings_local.py must define: {', '.join(_missing)}")

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS
