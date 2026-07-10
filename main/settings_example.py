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
# ]
LOCAL_APPS: list[str] = []
