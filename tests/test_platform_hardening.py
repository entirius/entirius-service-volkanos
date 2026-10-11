# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Service hardening: DRF_NUM_PROXIES + volkanos.E001, JWT-only default authentication + volkanos.E002, staff-only
OpenAPI, failed-login throttle on api/token/."""

import base64

import pytest
from django.conf import settings as django_settings
from django.contrib.auth import get_user_model
from django.core import checks
from django.core.cache import caches
from django.urls import path as url_path
from drf_spectacular.generators import SchemaGenerator
from drf_spectacular.settings import IMPORT_STRINGS, SPECTACULAR_DEFAULTS, SpectacularSettings
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.throttling import BaseThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.platform.checks import CHECK_TAG, check_default_authentication, check_num_proxies
from apps.platform.token_views import TaggedTokenObtainPairView, TaggedTokenRefreshView
from main import urls as service_urls
from main.security import SCHEMA_SERVE_PERMISSIONS, with_num_proxies, with_schema_access
from tests.conftest import requires_access

PASSWORD = "correct-horse-battery"  # noqa: S105 — throwaway test user
SCHEMA_PATHS = ("/api/schema/", "/api/schema/swagger-ui/", "/api/schema/redoc/")

# --- DRF_NUM_PROXIES ----------------------------------------------------------------------------------------------


def test_num_proxies_is_copied_into_rest_framework_only_when_set():
    assert with_num_proxies({"A": 1}, None) == {"A": 1}
    assert with_num_proxies({"A": 1}, 1) == {"A": 1, "NUM_PROXIES": 1}


def test_running_settings_carry_the_environment_value():
    assert django_settings.REST_FRAMEWORK.get("NUM_PROXIES") == django_settings.DRF_NUM_PROXIES


def test_one_proxy_trusts_only_the_last_forwarded_hop(settings):
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK, "NUM_PROXIES": 1}
    factory = APIRequestFactory()
    spoofed = factory.get("/", HTTP_X_FORWARDED_FOR="6.6.6.6, 198.51.100.7, 203.0.113.9")
    honest = factory.get("/", HTTP_X_FORWARDED_FOR="198.51.100.7, 203.0.113.9")
    assert BaseThrottle().get_ident(spoofed) == BaseThrottle().get_ident(honest) == "203.0.113.9"


@pytest.mark.parametrize("debug", [True, False])
def test_e001_fires_without_num_proxies_in_any_debug(settings, debug):
    settings.DEBUG, settings.DRF_NUM_PROXIES = debug, None
    messages = check_num_proxies()
    assert [m.id for m in messages] == ["volkanos.E001"]
    assert messages[0].level == checks.ERROR


@pytest.mark.parametrize("num_proxies", [0, 1])
def test_e001_silent_when_set(settings, num_proxies):
    settings.DEBUG, settings.DRF_NUM_PROXIES = False, num_proxies
    assert check_num_proxies() == []


def test_e001_is_a_deployment_check_only(settings):
    settings.DRF_NUM_PROXIES = None
    deploy = checks.run_checks(tags=[CHECK_TAG], include_deployment_checks=True)
    assert "volkanos.E001" in [m.id for m in deploy]
    assert "volkanos.E001" not in [m.id for m in checks.run_checks()]


def test_login_settings_declare_the_per_login_counter():
    assert django_settings.AUTH_TOKEN_MAX_FAILURES_PER_USER == 50
    assert django_settings.AUTH_TOKEN_USER_FAILURE_WINDOW_S == 3600


# --- default authentication ---------------------------------------------------------------------------------------

JWT_ONLY = ["rest_framework_simplejwt.authentication.JWTAuthentication"]
MATRIX_PRODUCTS = "/api/matrix/v2/no-such-channel/products/"


class _UndeclaredPublicView(APIView):
    """A module view that declares no authentication classes: it gets the service default."""

    permission_classes = [AllowAny]

    def get(self, request) -> Response:
        return Response({})


def _basic(username: str, password: str) -> dict:
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"HTTP_AUTHORIZATION": f"Basic {token}"}


def _without_default_authentication(rest_framework: dict) -> dict:
    return {k: v for k, v in rest_framework.items() if k != "DEFAULT_AUTHENTICATION_CLASSES"}


def test_default_authentication_is_jwt_only():
    assert django_settings.REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] == JWT_ONLY


@pytest.mark.django_db
def test_view_without_declared_classes_ignores_basic_credentials():
    _user("staffer", is_staff=True)
    view, factory = _UndeclaredPublicView.as_view(), APIRequestFactory()
    credentials = [{}, _basic("staffer", "wrong-password"), _basic("staffer", PASSWORD)]
    responses = [view(factory.get("/", **headers)) for headers in credentials]
    assert [r.status_code for r in responses] == [200, 200, 200]
    assert not [r for r in responses if "WWW-Authenticate" in r]


@pytest.mark.skipif("django_matrix" not in django_settings.INSTALLED_APPS, reason="django_matrix is not enabled")
@pytest.mark.django_db
def test_public_catalogue_route_answers_the_same_for_any_basic_credentials(client):
    _user("staffer", is_staff=True)
    credentials = [{}, _basic("staffer", "wrong-password"), _basic("staffer", PASSWORD)]
    responses = [client.get(MATRIX_PRODUCTS, **headers) for headers in credentials]
    assert len({r.status_code for r in responses}) == 1
    assert not [r for r in responses if "WWW-Authenticate" in r]


@pytest.mark.parametrize("name", ["BasicAuthentication", "SessionAuthentication"])
def test_e002_fires_on_a_password_class_in_the_defaults(settings, name):
    classes = [*JWT_ONLY, f"rest_framework.authentication.{name}"]
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK, "DEFAULT_AUTHENTICATION_CLASSES": classes}
    messages = check_default_authentication()
    assert [m.id for m in messages] == ["volkanos.E002"]
    assert messages[0].level == checks.ERROR
    assert name in messages[0].msg


def test_e002_fires_when_the_defaults_are_left_to_drf(settings):
    settings.REST_FRAMEWORK = _without_default_authentication(settings.REST_FRAMEWORK)
    assert [m.id for m in check_default_authentication()] == ["volkanos.E002"]


@pytest.mark.parametrize("classes", [JWT_ONLY, []])
def test_e002_silent_without_a_password_class(settings, classes):
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK, "DEFAULT_AUTHENTICATION_CLASSES": classes}
    assert check_default_authentication() == []


def test_e002_is_a_deployment_check_only(settings):
    settings.REST_FRAMEWORK = _without_default_authentication(settings.REST_FRAMEWORK)
    deploy = checks.run_checks(tags=[CHECK_TAG], include_deployment_checks=True)
    assert "volkanos.E002" in [m.id for m in deploy]
    assert "volkanos.E002" not in [m.id for m in checks.run_checks()]


# --- OpenAPI ------------------------------------------------------------------------------------------------------


def test_schema_access_helper():
    staff_only = with_schema_access({"TITLE": "x"}, public=False)
    assert staff_only["SERVE_PERMISSIONS"] == SCHEMA_SERVE_PERMISSIONS
    assert all("Basic" not in cls for cls in staff_only["SERVE_AUTHENTICATION"])
    assert with_schema_access({"TITLE": "x"}, public=True) == {"TITLE": "x"}


def _staff_only_views() -> dict:
    """The three schema views as drf-spectacular builds them from the staff-only settings (it reads them at import)."""
    serve = SpectacularSettings(
        user_settings=with_schema_access(django_settings.SPECTACULAR_SETTINGS, public=False),
        defaults=SPECTACULAR_DEFAULTS,
        import_strings=IMPORT_STRINGS,
    )
    kwargs = {"permission_classes": serve.SERVE_PERMISSIONS, "authentication_classes": serve.SERVE_AUTHENTICATION}
    return {
        SCHEMA_PATHS[0]: SpectacularAPIView.as_view(**kwargs),
        SCHEMA_PATHS[1]: SpectacularSwaggerView.as_view(url_name="schema", **kwargs),
        SCHEMA_PATHS[2]: SpectacularRedocView.as_view(url_name="schema", **kwargs),
    }


def _user(username: str, *, is_staff: bool = False):
    return get_user_model().objects.create_user(
        username=username, email=f"{username}@example.com", password=PASSWORD, is_staff=is_staff
    )


def _bearer(user) -> dict:
    return {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(user).access_token}"}


@pytest.mark.django_db
def test_staff_only_schema_views_by_principal():
    views, factory = _staff_only_views(), APIRequestFactory()
    principals = {401: {}, 403: _bearer(_user("customer")), 200: _bearer(_user("staffer", is_staff=True))}
    for path, view in views.items():
        for expected, headers in principals.items():
            assert view(factory.get(path, **headers)).status_code == expected, (path, expected)


@pytest.mark.django_db
def test_staff_session_opens_the_browser_ui():
    request = APIRequestFactory().get(SCHEMA_PATHS[1])
    request.user = _user("staffer", is_staff=True)
    assert _staff_only_views()[SCHEMA_PATHS[1]](request).status_code == 200


@pytest.mark.django_db
def test_live_schema_ui_follows_the_environment_setting(client):
    assert (SpectacularAPIView.permission_classes == [AllowAny]) is django_settings.API_SCHEMA_PUBLIC
    expected = 200 if django_settings.API_SCHEMA_PUBLIC else 401
    assert [client.get(path).status_code for path in SCHEMA_PATHS[1:]] == [expected, expected]


def _post_tags(patterns: list) -> set[str]:
    paths = SchemaGenerator(patterns=patterns).get_schema(request=None, public=True)["paths"]
    return {tag for item in paths.values() for tag in item["post"]["tags"]}


def test_token_routes_carry_the_authentication_tag():
    """The served pair (the login `main/urls.py` picks, refresh) and the login of a service without access."""
    served = [p for p in service_urls.urlpatterns if getattr(p, "name", None) in ("token_obtain_pair", "token_refresh")]
    fallback = [url_path("api/token/", TaggedTokenObtainPairView.as_view())]
    assert len(served) == 2
    assert _post_tags(served) == _post_tags(fallback) == {"Authentication"}
    assert served[1].callback.view_class is TaggedTokenRefreshView


# --- api/token/ failed-login throttle -----------------------------------------------------------------------------


@pytest.fixture
def login_cache(settings):
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "10b"}}
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    cache = caches["default"]
    cache.clear()
    return cache


@pytest.fixture
def staff(login_cache):
    return _user("staffer", is_staff=True)


def _login(client, username: str, password: str, addr: str = "192.0.2.10", **extra) -> int:
    body = {"username": username, "password": password}
    return client.post("/api/token/", body, content_type="application/json", REMOTE_ADDR=addr, **extra).status_code


@requires_access
@pytest.mark.django_db
def test_ten_failures_block_the_user_on_that_address_even_with_the_right_password(client, staff):
    assert [_login(client, "staffer", "wrong") for _ in range(10)] == [401] * 10
    response = client.post(
        "/api/token/",
        {"username": "staffer", "password": PASSWORD},
        content_type="application/json",
        REMOTE_ADDR="192.0.2.10",
    )
    assert response.status_code == 429
    assert response["Retry-After"] == str(django_settings.AUTH_TOKEN_FAILURE_WINDOW_S)
    assert _login(client, "staffer", PASSWORD, addr="192.0.2.99") == 200


@requires_access
@pytest.mark.django_db
def test_hundred_failures_over_usernames_block_the_address(client, staff):
    assert {_login(client, f"guess{i}", "wrong") for i in range(100)} == {401}
    assert _login(client, "staffer", PASSWORD) == 429
    assert _login(client, "staffer", PASSWORD, addr="192.0.2.99") == 200


@requires_access
@pytest.mark.django_db
def test_fifty_failures_over_addresses_block_the_username_for_its_window(client, staff):
    assert {_login(client, "staffer", "wrong", addr=f"198.51.100.{i}") for i in range(50)} == {401}
    response = client.post(
        "/api/token/",
        {"username": "staffer", "password": PASSWORD},
        content_type="application/json",
        REMOTE_ADDR="192.0.2.99",
    )
    assert response.status_code == 429
    assert response["Retry-After"] == str(django_settings.AUTH_TOKEN_USER_FAILURE_WINDOW_S)


@requires_access
@pytest.mark.django_db
def test_successful_logins_are_never_counted(client, staff, login_cache):
    assert {_login(client, "staffer", PASSWORD) for _ in range(50)} == {200}
    assert not login_cache._cache


@requires_access
@pytest.mark.django_db
def test_success_clears_the_user_address_counter(client, staff):
    for _ in range(2):
        assert [_login(client, "staffer", "wrong") for _ in range(9)] == [401] * 9
        assert _login(client, "staffer", PASSWORD) == 200


@requires_access
@pytest.mark.django_db
def test_cache_keys_hold_neither_username_nor_address(client, staff, login_cache):
    _login(client, "staffer", "wrong")
    keys = list(login_cache._cache)
    assert len(keys) == 3  # user+address, address, user (per-login limit)
    assert not [k for k in keys if "staffer" in k or "192.0.2.10" in k]


@requires_access
@pytest.mark.django_db
def test_spoofed_leading_forwarded_entry_keeps_the_visitor_blocked(client, staff, settings):
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK, "NUM_PROXIES": 1}
    honest = {"HTTP_X_FORWARDED_FOR": "198.51.100.7, 203.0.113.9"}
    assert [_login(client, "staffer", "wrong", **honest) for _ in range(10)] == [401] * 10
    spoofed = {"HTTP_X_FORWARDED_FOR": "6.6.6.6, 198.51.100.7, 203.0.113.9"}
    assert _login(client, "staffer", PASSWORD, **spoofed) == 429


@requires_access
@pytest.mark.django_db
def test_padded_username_hits_the_same_counter(client, staff):
    assert [_login(client, "staffer", "wrong") for _ in range(10)] == [401] * 10
    assert _login(client, " staffer\t", PASSWORD) == 429
