# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Security setting helpers, applied by main/settings.py after the environment's settings_local.

Pure functions over plain dicts — no Django imports, so settings.py can call them and tests can call them directly.
"""

SCHEMA_SERVE_PERMISSIONS = ["rest_framework.permissions.IsAdminUser"]
# JWT for API clients, the Django admin session for the browser UIs; never Basic (a password per request).
SCHEMA_SERVE_AUTHENTICATION = [
    "rest_framework_simplejwt.authentication.JWTAuthentication",
    "rest_framework.authentication.SessionAuthentication",
]


def with_num_proxies(rest_framework: dict, num_proxies: int | None) -> dict:
    """``REST_FRAMEWORK`` with ``NUM_PROXIES`` set; unchanged when the environment left it None (DRF's default)."""
    if num_proxies is None:
        return rest_framework
    return {**rest_framework, "NUM_PROXIES": num_proxies}


def with_schema_access(spectacular: dict, *, public: bool) -> dict:
    """``SPECTACULAR_SETTINGS`` serving the OpenAPI document and its UIs to staff only, unless ``public``."""
    if public:
        return spectacular
    return {
        **spectacular,
        "SERVE_PERMISSIONS": SCHEMA_SERVE_PERMISSIONS,
        "SERVE_AUTHENTICATION": SCHEMA_SERVE_AUTHENTICATION,
    }
