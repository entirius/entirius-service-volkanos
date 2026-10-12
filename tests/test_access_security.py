# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The access gate's contract over the service's real route set (the service half of the access security test plan).

Public set untouched, principal sweep of the admin set (D12: a token is anonymous there), route-map invariants, path
mutations, OpenAPI exposure, CORS. Every principal's secret is generated here.
"""

import json
import re
import secrets
import time
from collections import Counter
from dataclasses import dataclass
from unittest import mock

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.urls import Resolver404, ResolverMatch, resolve

from tests.conftest import requires_access

pytestmark = requires_access

JWT_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication"
SESSION_AUTH = "rest_framework.authentication.SessionAuthentication"
GATE_AUTHENTICATORS = frozenset({JWT_AUTH, SESSION_AUTH})
ADMIN_CLASS_NAMES = frozenset({"IsAdminUser", "IsSuperUser"})
SWEEP_METHODS = ("GET", "POST")
PUBLIC_SWEEP_BUDGET_S = 1.0
TOKEN_RE = re.compile(r"ent_api_[A-Za-z0-9_-]{43}")
SAMPLE_VALUES = ("1", "x", "00000000-0000-4000-8000-000000000001")
_CONVERTER = re.compile(r"<(?:\w+:)?\w+>")
_GROUP = re.compile(r"\(\?P<\w+>(?:[^()]|\([^()]*\))*\)")


@dataclass(frozen=True)
class Who:
    """A principal of the sweep: ``user`` is both the JWT bearer and the session user; ``headers`` extra META."""

    name: str
    user: object = None
    headers: tuple[tuple[str, str], ...] = ()


def bearer(user) -> tuple[tuple[str, str], ...]:
    from rest_framework_simplejwt.tokens import AccessToken

    return (("HTTP_AUTHORIZATION", f"Bearer {AccessToken.for_user(user)}"),)


def make_user(**flags):
    username = f"access-{secrets.token_hex(6)}"
    return get_user_model().objects.create_user(username=username, password=secrets.token_urlsafe(16), **flags)


def gate_request(route: str, callback, method: str, who: Who):
    """A request as the gate sees it after resolve: the route's ``ResolverMatch``, the principal's JWT and session."""
    request = RequestFactory().generic(method, "/", **dict(who.headers))
    request.resolver_match = ResolverMatch(callback, (), {}, route=route)
    request.user = who.user or AnonymousUser()
    request._dont_enforce_csrf_checks = True
    return request


def decide(info, callback, method: str, who: Who):
    from django_access.services import gate

    return gate.decide(gate_request(info.route, callback, method, who), callback)


def outcome(decision) -> tuple:
    return decision.allow, decision.status, decision.issue, decision.bypass


# --- public set ---------------------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_public_routes_are_allowed_without_queries_or_authentication(
    access_routes, access_report, django_assert_num_queries
):
    from rest_framework_simplejwt.authentication import JWTAuthentication

    customer = make_user()
    principals = (
        Who("anonymous"),
        Who("customer", customer, bearer(customer)),
        Who("garbage", headers=(("HTTP_AUTHORIZATION", f"Bearer {secrets.token_hex(12)}"),)),
    )
    public = [(info, callback) for info, callback in access_routes if not info.admin]
    with mock.patch.object(JWTAuthentication, "authenticate") as authenticate, django_assert_num_queries(0):
        started = time.perf_counter()
        refused = [
            (info.route, who.name)
            for info, callback in public
            for who in principals
            if not decide(info, callback, "GET", who).allow
        ]
        elapsed = time.perf_counter() - started
    assert refused == []
    authenticate.assert_not_called()
    assert elapsed < PUBLIC_SWEEP_BUDGET_S
    calls = len(public) * len(principals)
    print(f"\npublic sweep: {len(public)} routes x {len(principals)} principals, {elapsed * 1e6 / calls:.1f} us/call")
    print("non-admin per module:", dict(Counter(item["owner"] for item in access_report["non_admin"])))
    print("non-admin per audience:", dict(Counter(item["audience"] for item in access_report["non_admin"])))


# --- admin set principal sweep -------------------------------------------------------------------------------------


def gate_sees(info, callback, who: Who) -> bool:
    """Whether the gate finds the principal: a DRF view only through its JWT/session authenticators."""
    if who.user is None:
        return False
    return not hasattr(callback, "cls") or bool(GATE_AUTHENTICATORS & set(info.auth))


def expected(info, callback, method: str, who: Who) -> tuple:
    """The contract's answer per principal (README § Gate, § Built-in roles)."""
    from django_access.services import route_map

    if not gate_sees(info, callback, who):
        return (True, 200, None, False) if info.self_auth else (False, 401, "NOT_AUTHENTICATED", False)
    needed = route_map.required_permission(info, method)
    if who.user.is_superuser:
        return True, 200, None, superuser_writes(needed, method)
    if not who.user.is_staff:
        return False, 403, "STAFF_ONLY", False
    if needed == "staff.baseline" or (who.name == "viewer" and viewer_reads(needed)):
        return True, 200, None, False
    return False, 403, "ACCESS_DENIED", False


def superuser_writes(needed: str, method: str) -> bool:
    """A bypass row: a write permission, or an unsafe method behind ``superuser.only`` (the Django admin, D32)."""
    from django_access.catalogue.areas import SUPERUSER_ONLY

    if needed == SUPERUSER_ONLY:
        return method not in ("GET", "HEAD", "OPTIONS")
    return needed.endswith(":write")


def viewer_reads(needed: str) -> bool:
    return needed.endswith(":read") and not needed.startswith("access.manage:")


@pytest.fixture
def admin_principals(db) -> list[Who]:
    from django_access.models import Role
    from django_access.services import access_service
    from django_access.services.permissions import VIEWER

    viewer = make_user(is_staff=True)
    access_service.grant_role(Role.objects.get(key=VIEWER), user=viewer, actor=access_service.Actor())
    users = {
        "customer": make_user(),
        "staff_no_role": make_user(is_staff=True),
        "viewer": viewer,
        "superuser": make_user(is_staff=True, is_superuser=True),
        "superuser_not_staff": make_user(is_superuser=True),
    }
    return [Who(name, user, bearer(user)) for name, user in users.items()]


@pytest.fixture
def every_scope_headers(db) -> tuple[tuple[str, str], ...]:
    """A publishable token with every publishable scope, a secret one with every secret scope (never mixed)."""
    from datetime import timedelta

    from django.utils import timezone
    from django_access.catalogue import registry
    from django_access.services import access_service, tokens

    actor = access_service.Actor()
    application = tokens.create_application("access sweep", actor=actor)
    scopes = registry.scopes()
    _, public = tokens.issue_token(application, scopes=[s.key for s in scopes if s.publishable], actor=actor)
    _, secret = tokens.issue_token(
        application,
        scopes=[s.key for s in scopes if not s.publishable],
        expires_at=timezone.now() + timedelta(days=30),
        actor=actor,
    )
    return ("HTTP_X_API_KEY", public), ("HTTP_X_API_ADMIN_KEY", secret)


def test_admin_routes_answer_every_principal_per_contract(access_routes, admin_principals, every_scope_headers):
    anonymous, token = Who("anonymous"), Who("token_every_scope", headers=every_scope_headers)
    admin = [(info, callback) for info, callback in access_routes if info.admin]
    wrong = []
    for (info, callback), method in ((entry, method) for entry in admin for method in SWEEP_METHODS):
        anonymous_answer = outcome(decide(info, callback, method, anonymous))
        if outcome(decide(info, callback, method, token)) != anonymous_answer:
            wrong.append((info.route, method, token.name, "differs from anonymous"))
        for who in (anonymous, *admin_principals):
            got, want = outcome(decide(info, callback, method, who)), expected(info, callback, method, who)
            if got != want:
                wrong.append((info.route, method, who.name, got, want))
    assert wrong == [], f"{len(wrong)} cells off contract, first: {wrong[:10]}"


def test_viewer_never_runs_a_pii_export(access_routes, admin_principals):
    viewer = next(who for who in admin_principals if who.name == "viewer")
    exports = [(info, callback) for info, callback in access_routes if info.method_levels.get("GET") == "write"]
    assert exports
    assert [info.route for info, callback in exports if decide(info, callback, "GET", viewer).allow] == []


# --- invariants ----------------------------------------------------------------------------------------------------


def test_route_map_invariants_hold(access_report):
    assert access_report["unmapped_admin"] == []
    assert access_report["foreign_rule_matches"] == []
    other_auth = [item for item in access_report["admin"] if set(item["auth"]) - GATE_AUTHENTICATORS]
    assert [item["route"] for item in other_auth if item["self_auth"]] == []
    print("\nadmin views on authenticators the gate does not run:", [item["route"] for item in other_auth])
    print("admin_not_self_auth:", len(access_report["admin_not_self_auth"]))


def is_admin_class(item) -> bool:
    """An ``IsAdminUser``/``IsSuperUser`` class or subclass, also inside a DRF ``&``/``|`` composite."""
    if hasattr(item, "op2_class"):
        return is_admin_class(item.op1_class) or is_admin_class(item.op2_class)
    return isinstance(item, type) and any(base.__name__ in ADMIN_CLASS_NAMES for base in item.__mro__)


def test_no_public_view_requires_an_admin(access_routes):
    carriers = []
    for info, callback in access_routes:
        view = getattr(callback, "cls", None)
        if info.admin or view is None:
            continue
        declared = (getattr(callback, "initkwargs", None) or {}).get("permission_classes", view.permission_classes)
        if any(is_admin_class(item) for item in declared):
            carriers.append(info.route)
    assert carriers == []


# --- path mutations ------------------------------------------------------------------------------------------------


def sample_path(route: str, value: str) -> str:
    """A concrete path of a route string: converters and named groups → ``value``, regex anchors dropped."""
    path = _CONVERTER.sub(value, _GROUP.sub(value, route))  # groups first: they contain ``<name>``
    return "/" + path.replace("^", "").replace("$", "").replace("\\.", ".").replace("/?", "/")


def admin_sample(info) -> str | None:
    """A path that resolves back to the route itself, or ``None``."""
    for value in SAMPLE_VALUES:
        path = sample_path(info.route, value)
        try:
            if resolve(path).route == info.route:
                return path
        except Resolver404:
            continue
    return None


def mutations(path: str) -> dict[str, str]:
    second = path.index("/", 1)
    first, rest = path[1:second], path[second:]
    stem = path.rstrip("/")
    return {
        "slash": stem if path.endswith("/") else path + "/",
        "double_slash": f"/{first}/{rest}",
        "encoded_slash": f"/{first}%2F{rest[1:]}",
        "upper_segment": f"/{first.upper()}{rest}",
        "matrix_param": stem + ";x=1" + ("/" if path.endswith("/") else ""),
        "format_suffix": stem + ".json",
    }


def view_of(callback):
    return getattr(callback, "cls", None) or getattr(callback, "view_class", None) or callback


def landing(path: str):
    """``(RouteInfo, view)`` the path resolves to, or ``None`` on a 404."""
    from django_access.services import route_map

    try:
        match = resolve(path)
    except Resolver404:
        return None
    return route_map.classify(match.route, match.func), view_of(match.func)


def test_path_mutations_never_reach_an_admin_view_outside_the_admin_set(access_routes):
    """A mutation reaching the same admin view through a non-admin route fails; one landing on another, public view
    (e.g. ``health;x=1/`` → a public ``<str:key>/`` route) never runs the admin view and is listed."""
    escaped, elsewhere, area_changes, unsampled = [], [], [], []
    admin = [(info, callback) for info, callback in access_routes if info.admin]
    for info, callback in admin:
        if (path := admin_sample(info)) is None:
            unsampled.append(info.route)
            continue
        for name, mutated in mutations(path).items():
            if (landed := landing(mutated)) is None:
                continue
            target, view = landed
            if not target.admin:
                (escaped if view is view_of(callback) else elsewhere).append((info.route, name, target.route))
            elif target.area != info.area:
                area_changes.append((info.route, name, target.area))
    assert escaped == []
    assert len(unsampled) * 100 <= len(admin), f"too many routes without a sample path: {unsampled[:10]}"
    print(f"\nmutations: {len(unsampled)} admin routes unsampled; on other public views: {elsewhere}")
    print(f"area changes: {area_changes}")


# --- OpenAPI exposure ----------------------------------------------------------------------------------------------


def property_names(node) -> set[str]:
    if isinstance(node, list):
        return set().union(*map(property_names, node))
    if not isinstance(node, dict):
        return set()
    own = set(node["properties"]) if isinstance(node.get("properties"), dict) else set()
    return own.union(*map(property_names, node.values()))


@pytest.mark.django_db
def test_openapi_document_exposes_the_key_scheme_and_no_secret(client):
    from django_access.openapi import SCHEME_NAME, key_route_matcher
    from drf_spectacular.generators import SchemaGenerator

    document = SchemaGenerator().get_schema(request=None, public=True)
    assert SCHEME_NAME in document["components"]["securitySchemes"]
    matcher = key_route_matcher()
    key_ops = [
        operation
        for path, item in document["paths"].items()
        if matcher.fullmatch(path)
        for operation in item.values()
        if isinstance(operation, dict) and "responses" in operation
    ]
    assert key_ops
    assert all(
        operation["security"] and all(SCHEME_NAME in req for req in operation["security"]) for operation in key_ops
    )
    assert not TOKEN_RE.search(json.dumps(document, default=str))
    assert "key_hash" not in property_names(document)
    print(f"\napi/schema/ anonymous GET: HTTP {client.get('/api/schema/', {'format': 'json'}).status_code}")


# --- CORS ----------------------------------------------------------------------------------------------------------


def test_admin_key_header_is_not_allowed_cross_origin():
    assert "x-api-admin-key" not in {header.lower() for header in settings.CORS_ALLOW_HEADERS}
