# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Shared fixtures of the access tests: the service's real route set, classified by the access route map.

``django_access`` is imported lazily — the service runs without it, and its tests then skip.
"""

import io
import json

import pytest
from django.conf import settings

requires_access = pytest.mark.skipif(
    "django_access" not in settings.INSTALLED_APPS, reason="django_access is not installed"
)


@pytest.fixture(scope="session")
def access_routes() -> list:
    """``(RouteInfo, callback)`` per route string, the first one the resolver would match."""
    from django_access.services import route_map

    callbacks: dict = {}
    for route, callback in route_map.walk():
        callbacks.setdefault(route, callback)
    return [(route_map.classify(route, callback), callback) for route, callback in callbacks.items()]


@pytest.fixture(scope="session")
def access_report(tmp_path_factory) -> dict:
    """The route audit's JSON report (non-admin audiences, admin entries, foreign rule matches)."""
    from django_access.services import route_map

    path = tmp_path_factory.mktemp("access") / "routes.json"
    route_map.audit_routes(io.StringIO(), json_path=str(path))
    return json.loads(path.read_text())
