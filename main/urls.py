# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""URL routing for the Entirius Volkanos service."""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("admin/", admin.site.urls),
    # JWT for module admin APIs (v2, IsAdminUser) and the CMS admin panel.
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    # Volkanos modules wire their include() here as they are adopted.
]

# Adopted modules route only where the environment enables them (LOCAL_APPS in settings_local).
if "django_regional" in settings.INSTALLED_APPS:
    urlpatterns.append(path("", include("django_regional.urls")))
if "django_pim" in settings.INSTALLED_APPS:
    urlpatterns.append(path("", include("django_pim.urls")))
if "django_pricemanager" in settings.INSTALLED_APPS:
    urlpatterns.append(path("", include("django_pricemanager.urls")))
if "django_pim_translator" in settings.INSTALLED_APPS:
    urlpatterns.append(path("", include("django_pim_translator.urls")))
if "django_vat_validator" in settings.INSTALLED_APPS:
    urlpatterns.append(path("", include("django_vat_validator.urls")))
if "django_faq" in settings.INSTALLED_APPS:
    urlpatterns.append(path("", include("django_faq.urls")))
if "django_munin" in settings.INSTALLED_APPS:
    urlpatterns.append(path("", include("django_munin.urls")))
if "django_agreements" in settings.INSTALLED_APPS:
    urlpatterns.append(path("", include("django_agreements.urls")))
if "django_deliverypoints" in settings.INSTALLED_APPS:
    urlpatterns.append(path("", include("django_deliverypoints.urls")))
if "django_qms" in settings.INSTALLED_APPS:
    urlpatterns.append(path("", include("django_qms.urls")))
if "django_email" in settings.INSTALLED_APPS:
    urlpatterns.append(path("", include("django_email.urls")))
if "django_enrichment" in settings.INSTALLED_APPS:
    urlpatterns.append(path("", include("django_enrichment.urls")))
if "django_contentdb" in settings.INSTALLED_APPS:
    urlpatterns.append(path("", include("django_contentdb.urls")))
if "django_accounts" in settings.INSTALLED_APPS:
    urlpatterns.append(path("", include("django_accounts.urls")))
if "django_suppliers" in settings.INSTALLED_APPS:
    urlpatterns.append(path("", include("django_suppliers.urls")))
if "django_contentdb_translator" in settings.INSTALLED_APPS:
    urlpatterns.append(path("", include("django_contentdb_translator.urls")))
if "django_vault" in settings.INSTALLED_APPS:
    urlpatterns.append(path("", include("django_vault.urls")))
if "django_reviews" in settings.INSTALLED_APPS:
    urlpatterns.append(path("", include("django_reviews.urls")))
if "django_matrix" in settings.INSTALLED_APPS:
    urlpatterns.append(path("", include("django_matrix.urls")))
if "django_checkout" in settings.INSTALLED_APPS:
    urlpatterns.append(path("", include("django_checkout.urls")))
if "django_checkout_voucher" in settings.INSTALLED_APPS:
    urlpatterns.append(path("", include("django_checkout_voucher.urls")))
if "django_returns" in settings.INSTALLED_APPS:
    urlpatterns.append(path("", include("django_returns.urls")))
if "django_crm" in settings.INSTALLED_APPS:
    urlpatterns.append(path("", include("django_crm.urls")))
if "django_loyalty" in settings.INSTALLED_APPS:
    urlpatterns.append(path("", include("django_loyalty.urls")))

if settings.DEBUG:
    from django.conf.urls.static import static

    # Dev server serves media (product images, CMS uploads) — production fronts them
    # with a web server.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
