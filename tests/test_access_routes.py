# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Route coverage of the access gate: every admin route of the service has an area, key routes stay public."""

import re

import pytest
from django.conf import settings
from django.urls import resolve

from tests.conftest import requires_access

GATE = "django_access.middleware.AccessGateMiddleware"
MIN_ADMIN_ROUTES = 440
# The X-API-ADMIN-KEY erase routes: token routes under an admin-looking path, never in the admin set.
ERASE_ROUTES = (
    "/api-admin/checkout/{version}/{channel_idx}/customer/delete",
    "/api-admin/accounts/{version}/{channel_idx}/customer/delete",
)


def scope_sample(doc_route: str) -> str:
    """A concrete path of a token scope's doc route: every ``{name}`` → ``1``, ``/**`` → ``/``."""
    return re.sub(r"\{[^}]+\}", "1", doc_route.replace("/**", "/"))


def test_gate_middleware_is_last_when_the_app_is_installed():
    installed = "django_access" in settings.INSTALLED_APPS
    assert (GATE in settings.MIDDLEWARE) is installed
    if installed:
        assert settings.MIDDLEWARE[-1] == GATE


def skip_without_key_modules() -> None:
    """The route-set numbers hold for the platform module set (zeno); a bare service (CI) has no module routes."""
    from django_access.catalogue import registry

    if missing := {scope.module for scope in registry.scopes()} - set(settings.INSTALLED_APPS):
        pytest.skip(f"key modules not installed: {sorted(missing)}")


@requires_access
def test_every_admin_route_has_an_area(access_routes):
    admin = [info for info, _ in access_routes if info.admin]
    assert [info.route for info in admin if info.area is None] == []


@requires_access
def test_the_platform_module_set_has_its_admin_routes(access_routes):
    skip_without_key_modules()
    assert sum(info.admin for info, _ in access_routes) >= MIN_ADMIN_ROUTES


@requires_access
def test_token_scope_routes_stay_outside_the_admin_set():
    from django_access.catalogue import registry
    from django_access.services import route_map

    skip_without_key_modules()
    doc_routes = {route: scope.key for scope in registry.scopes() for route in scope.routes}
    assert len(set(doc_routes.values())) == 9
    assert set(ERASE_ROUTES) <= set(doc_routes)
    admin = []
    for doc_route in doc_routes:
        match = resolve(scope_sample(doc_route))
        if route_map.classify(match.route, match.func).admin:
            admin.append(match.route)
    assert admin == []
