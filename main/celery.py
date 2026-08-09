# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Celery application for the Entirius Volkanos service.

Module workers (QMS quantities, PIM thumbnails, pricemanager pricelists) run their
tasks through this app: `celery -A main worker -Q <queues>`.
Configuration comes from Django settings under the CELERY_ namespace
(per environment in settings_local.py, e.g. CELERY_BROKER_URL).
"""

import os

from django.conf import settings

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings")

app = Celery("volkanos")
app.config_from_object("django.conf:settings", namespace="CELERY")

# celery_once (used by module tasks) needs its own redis backend; environments
# without REDIS_URL simply don't run QueueOnce tasks.
if getattr(settings, "REDIS_URL", None):
    app.conf.ONCE = {
        "backend": "celery_once.backends.Redis",
        "settings": {"url": settings.REDIS_URL + "/3", "default_timeout": 60 * 60},
    }

app.autodiscover_tasks()
