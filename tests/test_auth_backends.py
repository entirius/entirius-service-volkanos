# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Customer endpoints authenticate the django_accounts Bearer token (AUTHENTICATION_BACKENDS)."""

import pytest
from django.conf import settings

JWT_BACKEND = "django_accounts.backends.JWTAccessBackend"
MODEL_BACKEND = "django.contrib.auth.backends.ModelBackend"
ACCOUNTS_INSTALLED = "django_accounts" in settings.INSTALLED_APPS


def test_model_backend_is_registered():
    """The Django admin login needs it whatever modules are installed."""
    assert MODEL_BACKEND in settings.AUTHENTICATION_BACKENDS


def test_jwt_backend_follows_django_accounts():
    """Registered first exactly when django_accounts is installed."""
    if ACCOUNTS_INSTALLED:
        assert settings.AUTHENTICATION_BACKENDS[0] == JWT_BACKEND
    else:
        assert JWT_BACKEND not in settings.AUTHENTICATION_BACKENDS


@pytest.mark.django_db
@pytest.mark.skipif(not ACCOUNTS_INSTALLED, reason="django_accounts not in LOCAL_APPS")
class TestCustomerMe:
    PASSWORD = "Customer-1234!"  # noqa: S105 - throwaway test user

    @pytest.fixture
    def channel(self):
        from django_accounts.models import Channel
        from django_regional.models import Language

        language, _ = Language.objects.get_or_create(
            iso2="en", defaults={"iso3": "eng", "name_en": "English", "name_pl": "Angielski"}
        )
        return Channel.objects.create(idx="test-channel", label="Test", language=language)

    @pytest.fixture
    def customer(self, channel):
        from allauth.account.models import EmailAddress
        from django.contrib.auth import get_user_model
        from django_accounts.models import Customer

        user = get_user_model().objects.create_user(
            username="customer@example.com", email="customer@example.com", password=self.PASSWORD
        )
        EmailAddress.objects.create(user=user, email=user.email, primary=True, verified=True)
        return Customer.objects.create(user=user, is_active=True, is_verified=True, source_channel=channel)

    def _me(self, client, channel, token=None):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        return client.get(f"/api/accounts/v1/{channel.idx}/customer/me/", headers=headers)

    def test_customer_token_reaches_customer_me(self, client, channel, customer):
        response = client.post(
            f"/api/accounts/v1/{channel.idx}/customer/tokens/",
            {"email": "customer@example.com", "password": self.PASSWORD},
            content_type="application/json",
        )
        assert response.status_code == 200
        token = response.json()["data"]["access"]

        assert self._me(client, channel, token).status_code == 200

    def test_no_token_is_401(self, client, channel):
        assert self._me(client, channel).status_code == 401
