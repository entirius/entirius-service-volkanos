# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""System checks of the environment's security configuration."""

from django.conf import settings
from django.core.checks import CheckMessage, Error

CHECK_TAG = "entirius_config"


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
