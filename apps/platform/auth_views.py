# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Staff login (``api/token/``) that stops answering a password guesser.

Only failed attempts count, per username + address and per address; a success clears the first counter and is never
counted. Cache keys carry hashes only — no username or address is stored.
"""

import hashlib
from collections.abc import Mapping

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.exceptions import AuthenticationFailed, Throttled
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import BaseThrottle
from rest_framework_simplejwt.views import TokenObtainPairView


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def failure_keys(request: Request) -> tuple[str, str]:
    """(per username + address, per address) counter keys; the address is DRF's ``get_ident`` (``NUM_PROXIES``)."""
    ident = BaseThrottle().get_ident(request)
    data = request.data if isinstance(request.data, Mapping) else {}
    # Stripped like SimpleJWT's CharField: " admin" logs into "admin", so it must hit the same counter.
    username = str(data.get(get_user_model().USERNAME_FIELD, "")).strip()
    per_user_ip = _digest(f"{username}\x00{ident}")
    return f"auth:fail:ui:{per_user_ip}", f"auth:fail:ip:{_digest(ident)}"


def _refuse_when_blocked(keys: tuple[str, str]) -> None:
    counts = cache.get_many(keys)
    per_user_ip, per_ip = counts.get(keys[0], 0), counts.get(keys[1], 0)
    if per_user_ip >= settings.AUTH_TOKEN_MAX_FAILURES_PER_USER_IP or per_ip >= settings.AUTH_TOKEN_MAX_FAILURES_PER_IP:
        raise Throttled(wait=settings.AUTH_TOKEN_FAILURE_WINDOW_S)


def _count_failure(key: str) -> None:
    window = settings.AUTH_TOKEN_FAILURE_WINDOW_S
    if cache.add(key, 1, timeout=window):
        return
    try:
        cache.incr(key)
    except ValueError:  # expired between add and incr
        cache.add(key, 1, timeout=window)


class ThrottledTokenObtainPairView(TokenObtainPairView):
    """SimpleJWT's token pair view behind a failed-login throttle."""

    def post(self, request: Request, *args, **kwargs) -> Response:
        keys = failure_keys(request)
        _refuse_when_blocked(keys)
        try:
            response = super().post(request, *args, **kwargs)
        except AuthenticationFailed:
            for key in keys:
                _count_failure(key)
            raise
        cache.delete(keys[0])
        return response

    def handle_exception(self, exc: Exception) -> Response:
        response = super().handle_exception(exc)
        if isinstance(exc, Throttled):  # the service's v1 error handler drops DRF's Retry-After
            response["Retry-After"] = str(settings.AUTH_TOKEN_FAILURE_WINDOW_S)
        return response
