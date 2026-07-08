# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Template for local settings - copy to main/settings_local.py and adjust.

settings_local.py is gitignored. Run with the override:
    DJANGO_SETTINGS_MODULE=main.settings_local
"""

from .settings import *

# Marks this as a dev box; unblocks dev-only Makefile targets (guard-dev). Keep in .env too.
ENVIRONMENT = "development"

DEBUG = True
ALLOWED_HOSTS = ["*"]

# DB is driven by the DATABASE_URL env var (see main/settings.py) — sqlite fallback,
# postgres e.g.: DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
