# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Staff login (``api/token/``) behind access' failed-login guard (``django_access.services.login_guard``)."""

import math

from django_access.services import login_guard
from rest_framework.exceptions import AuthenticationFailed, Throttled
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView


class ThrottledTokenObtainPairView(TokenObtainPairView):
    """SimpleJWT's token pair view behind a failed-login throttle."""

    def post(self, request: Request, *args, **kwargs) -> Response:
        username = login_guard.login_username(request)
        login_guard.refuse_when_blocked(request, username)
        try:
            response = super().post(request, *args, **kwargs)
        except AuthenticationFailed:
            login_guard.record_failure(request, username)
            raise
        login_guard.clear(request, username)
        return response

    def handle_exception(self, exc: Exception) -> Response:
        response = super().handle_exception(exc)
        if isinstance(exc, Throttled):  # the service's v1 error handler drops DRF's Retry-After
            response["Retry-After"] = str(math.ceil(exc.wait))
        return response
