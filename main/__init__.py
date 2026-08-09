# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Imported on Django startup so @shared_task in modules binds to this app.
from .celery import app as celery_app

__all__ = ["celery_app"]
