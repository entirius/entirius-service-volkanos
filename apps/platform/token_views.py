# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""SimpleJWT's token views with an explicit OpenAPI tag; no dependency on ``django_access``."""

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


@extend_schema_view(post=extend_schema(tags=["Authentication"]))
class TaggedTokenObtainPairView(TokenObtainPairView):
    """Staff login of a service without access: SimpleJWT's own view."""


@extend_schema_view(post=extend_schema(tags=["Authentication"]))
class TaggedTokenRefreshView(TokenRefreshView):
    """SimpleJWT's token refresh view."""
