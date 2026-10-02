# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.apps import AppConfig


class PlatformConfig(AppConfig):
    """Service-owned platform wiring: configuration checks and the throttled staff login. No models."""

    name = "apps.platform"
    label = "volkanos_platform"

    def ready(self) -> None:
        from django.core import checks

        from apps.platform.checks import CHECK_TAG, check_num_proxies

        checks.register(check_num_proxies, CHECK_TAG)
