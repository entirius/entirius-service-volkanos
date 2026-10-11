# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""System checks of the environment's security configuration."""

from django.conf import settings
from django.core.checks import CheckMessage, Error
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.settings import api_settings

CHECK_TAG = "entirius_config"
PASSWORD_AUTHENTICATION = (BasicAuthentication, SessionAuthentication)


def check_num_proxies(app_configs=None, **kwargs) -> list[CheckMessage]:
    """volkanos.E001 (``check --deploy``): ``DRF_NUM_PROXIES`` unset, so per-IP throttles key on a client header."""
    if settings.DRF_NUM_PROXIES is not None:
        return []
    return [
        Error(
            "per-IP throttles trust a client-supplied X-Forwarded-For while DRF_NUM_PROXIES is unset",
            hint="set DRF_NUM_PROXIES in settings_local: the number of proxies in front of the app (0 = none)",
            id="volkanos.E001",
        )
    ]


def check_default_authentication(app_configs=None, **kwargs) -> list[CheckMessage]:
    """volkanos.E002 (``check --deploy``): a view that declares no classes would check a password or a session."""
    defaults = api_settings.DEFAULT_AUTHENTICATION_CLASSES
    found = sorted(c.__name__ for c in defaults if issubclass(c, PASSWORD_AUTHENTICATION))
    if not found:
        return []
    return [
        Error(
            f"REST_FRAMEWORK DEFAULT_AUTHENTICATION_CLASSES holds {', '.join(found)}: every view without its own "
            "classes evaluates those credentials, outside the failed-login guard",
            hint="keep the service default (JWT only) and declare authentication_classes on the view that needs more",
            id="volkanos.E002",
        )
    ]
