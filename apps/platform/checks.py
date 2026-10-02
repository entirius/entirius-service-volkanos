# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""System checks of the environment's security configuration."""

from django.conf import settings
from django.core.checks import CheckMessage, Warning

CHECK_TAG = "entirius_config"


def check_num_proxies(app_configs=None, **kwargs) -> list[CheckMessage]:
    """volkanos.W001: production without ``DRF_NUM_PROXIES`` — per-IP throttles key on a client-supplied header."""
    if settings.DEBUG or settings.DRF_NUM_PROXIES is not None:
        return []
    return [
        Warning(
            "per-IP throttles trust a client-supplied X-Forwarded-For",
            hint="set DRF_NUM_PROXIES in settings_local (1 behind Cloudflare → Caddy → nginx)",
            id="volkanos.W001",
        )
    ]
