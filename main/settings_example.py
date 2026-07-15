# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Template for the REQUIRED per-environment config - copy to main/settings_local.py.

settings_local.py is gitignored; the service refuses to boot without it
(no explicit env type, DB and secret key means the environment was never
consciously configured). Must define: ENVIRONMENT, SECRET_KEY, DATABASES.
"""

import dj_database_url
from decouple import config

from .settings import BASE_DIR

# Marks this as a dev box; unblocks dev-only Makefile targets (guard-dev). Keep in .env too.
ENVIRONMENT = "development"

SECRET_KEY = "django-insecure-dev-only-change-me"
DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# DATABASE_URL drives the engine (e.g. postgres under entirius-zeno / CI);
# bare local dev falls back to sqlite.
DATABASES = {
    "default": dj_database_url.parse(
        config("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
    )
}

# Volkanos modules adopted in THIS environment (entirius-django-* app labels).
# Full django set (order matters: FK targets first — regional/utils before pim,
# pim/pricemanager before the pim satellites; leaves last):
# LOCAL_APPS = [
#     "django_regional",
#     "django_utils",
#     "django_utils_translator",
#     "django_pim",
#     "django_pricemanager",
#     "django_pim_csv",
#     "django_pim_translator",
#     "django_pim_export_to_magento_api",
#     "django_pim_export_to_magento_package",
#     "django_vat_validator",
#     "django_faq",
#     "django_munin",
#     "django_captcha",
#     "django_agreements",
#     "django_deliverypoints",
#     "django_qms",
#     "django_email",
#     "django_baselinker",
#     "django_crypt",
#     "django_enrichment",
#     "django_contentdb",
#     "django_accounts",
#     "django_suppliers",
#     "django_contentdb_translator",
#     "django_sitemap",
#     "django_accounts_export_to_magento_api",
#     "django_pricetuner",
#     "django_vault",
#     "django_reviews",
#     "django_matrix",
#     "django_checkout",
#     "django_checkout_voucher",  # must stay AFTER pim/checkout/accounts/crypt/email (FK targets)
#     "django_checkout_export_to_magento_api",
#     "django_checkout_import_from_magento_api",
#     "django_getresponse",
#     "django_returns",
#     "django_omnibus",
#     "django_crm",
#     "django_loyalty",
# ]
LOCAL_APPS: list[str] = []

# Voucher-flow secrets — REQUIRED per environment when django_checkout_voucher is adopted
# (module raises at first use, not at boot; never commit real values):
# VOUCHER_LOOKUP_HMAC_KEY — salt for HMAC-SHA256 voucher balance lookups (django_checkout_voucher);
# CRYPT_SALT — Fernet key for voucher code encryption (django_crypt), generate with:
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# VOUCHER_LOOKUP_HMAC_KEY = "change-me"
# CRYPT_SALT = "change-me-valid-fernet-key"

# Celery (module workers: QMS quantities, PIM thumbnails, pricemanager pricelists).
# The app lives in main/celery.py and reads CELERY_-prefixed keys from settings;
# REDIS_URL additionally feeds the celery_once backend used by some module tasks.
# CELERY_BROKER_URL = "amqp://guest:guest@localhost:5672//"
# REDIS_URL = "redis://localhost:6379"
# CELERY_RESULT_BACKEND = REDIS_URL + "/2"

# QMS quantities strategy per environment: "XRAY" (CSV/point-in-time driven, used by the
# Emporium demo package) or "ZULU" (storage-driven). Default in django_qms is ZULU.
# QMS_TYPE = "XRAY"
