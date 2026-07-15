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
    "django.contrib.sites",  # required by allauth (django_accounts)
    "django.contrib.postgres",  # GinIndex / full-text search in django_matrix
]

THIRD_PARTY_APPS = [
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    # Required by django_accounts (JWT auth, token blacklist, email verification, social login).
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
]

# Volkanos modules, adopted bottom-up stage by stage — override per environment in settings_local.
LOCAL_APPS: list[str] = []

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # CORS before CommonMiddleware — browser frontends call the API cross-origin;
    # allowed origins are strictly per environment (settings_local).
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
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

# Platform API contract: module public endpoints authenticate with X-API-KEY
# (checkout carts, contact forms) — the browser preflight must allow the header.
from corsheaders.defaults import default_headers  # noqa: E402

CORS_ALLOW_HEADERS = (*default_headers, "x-api-key")

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # v2 error envelope (error/debug_id) with v1 fallback — see main/v2_errors.py.
    "EXCEPTION_HANDLER": "main.v2_errors.volkanos_exception_handler",
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
DATA_DIR = BASE_DIR / "data"  # required by django_pim_export_to_magento_package
EXPORT_DIR = BASE_DIR / "export"  # required by django_pim_export_to_magento_package and django_checkout
PRIVATE_DIR = BASE_DIR / "private"  # required by django_accounts (customer file storage)

# Required by django_accounts: wishlist restructuring mode for the squashed 0024 data
# migration; 1 = fresh installations (no legacy wishlists to migrate).
MIGRATION_0023_MECHANISM = 1

# Read at import time by django_pim_csv / django_pim_export_to_magento_package / django_checkout
# (BI events); override per environment in settings_local.
BI_ENVIRONMENT = "development"
BI_BUSINESS_UNIT = "volkanos"

# Default language for PIM translations (django_pim_csv requires it).
T9N_DEFAULT_LANG = "en"

# Read at import time by django_checkout_export_to_magento_api tasks (module-level
# settings.MAGENTO2_* reads — boot fails with AttributeError without them);
# real endpoint/token per environment in settings_local.
MAGENTO2_URL_FOR_CHECKOUT_EXPORT = ""
MAGENTO2_TOKEN_FOR_CHECKOUT_EXPORT = ""

# django_checkout: route voucher validation through django_checkout_voucher signal handlers.
USE_VALIDATE_VOUCHERS_SIGNAL = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SITE_ID = 1  # django.contrib.sites (allauth)

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

# django_accounts refuses to boot without JWT_SECRET; default to SECRET_KEY, override per environment.
if "JWT_SECRET" not in globals():
    JWT_SECRET = SECRET_KEY  # noqa: F405

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS
