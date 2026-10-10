# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Create the first channel of a migrated, empty database (idempotent).

Usage: python scripts/first_channel.py <config.toml> (template: scripts/first-channel.example.toml), or
`make first-channel`. Languages and currencies, the channel in every enabled module, a storefront API key and
the customer rows the CMS login reads for each superuser (run `manage.py createsuperuser` first).
A step whose app is not enabled is skipped; a second run changes nothing.
"""

import io
import os
import sys
import tomllib
from pathlib import Path

import django
from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from django.db import transaction

BASE_DIR = Path(__file__).resolve().parent.parent
REQUIRED_KEYS = ("idx", "name", "default_language", "languages", "default_currency", "currencies", "country")
STOREFRONT_APPLICATION = "storefront"
STOREFRONT_SCOPE = "checkout.storefront"
CREATED, EXISTS, RAN = "created", "exists", "ran"
SYNC_COMMANDS = (
    ("django_contentdb", "sync_contentdb_languages"),
    ("django_contentdb", "sync_contentdb_channels"),
    ("django_faq", "sync_faq_channels"),
    ("django_deliverypoints", "sync_dp_channels"),
    ("django_agreements", "sync_agreement_channels"),
    ("django_pricefighter", "sync_pricefighter_channels"),
)


def load_config(path: str | Path) -> dict:
    """The `[channel]` table of the config file; ValueError names the first missing key."""
    with Path(path).open("rb") as handle:
        channel = tomllib.load(handle).get("channel", {})
    if missing := [key for key in REQUIRED_KEYS if key not in channel]:
        raise ValueError(f"{path}: [channel] is missing {', '.join(missing)}")
    return channel


def _report(step: str, state: str) -> None:
    print(f"first-channel: {step} {state}", flush=True)


def _state(created: bool) -> str:
    return CREATED if created else EXISTS


def _row(model_name: str, field: str, code: str):
    """One django_regional row by its code; exits with the missing code instead of a traceback."""
    model = apps.get_model("django_regional", model_name)
    if row := model.objects.filter(**{f"{field}__iexact": code}).first():
        return row
    sys.exit(f"first-channel: {model_name.lower()} {code!r} is not in django_regional — add it, then run again")


def _language(code: str):
    return _row("Language", "iso2", code)


def _currency(code: str):
    return _row("Currency", "iso3", code)


def _country(code: str):
    return _row("Country", "iso2", code)


def _languages(cfg: dict) -> list:
    """The channel's languages, its default always among them."""
    return [_language(code) for code in dict.fromkeys([cfg["default_language"], *cfg["languages"]])]


def _currencies(cfg: dict) -> list:
    return [_currency(code) for code in dict.fromkeys([cfg["default_currency"], *cfg["currencies"]])]


def _regional(cfg: dict) -> str:
    language = apps.get_model("django_regional", "Language")
    if language.objects.filter(iso2__iexact=cfg["default_language"]).exists():
        return EXISTS
    call_command("loaddata", "regional-defaults", stdout=io.StringIO())
    return CREATED


def _pim(cfg: dict) -> str:
    channels = apps.get_model("django_pim", "Channel").objects
    defaults = {
        "name": cfg["name"],
        "default_language": _language(cfg["default_language"]),
        "default_currency": _currency(cfg["default_currency"]),
        "is_default": not channels.exclude(idx=cfg["idx"]).filter(is_default=True).exists(),
    }
    channel, created = channels.update_or_create(idx=cfg["idx"], defaults=defaults)
    channel.languages.set(_languages(cfg))
    channel.currencies.set(_currencies(cfg))
    return _state(created)


def _sync(cfg: dict) -> str:
    for app, command in SYNC_COMMANDS:
        if apps.is_installed(app):
            call_command(command, stdout=io.StringIO())
    return RAN


def _pricemanager(cfg: dict) -> str:
    from django_pricemanager.services.channel_sync_service import sync_channels_from_pim

    sync_channels_from_pim()
    channels = apps.get_model("django_pricemanager", "Channel").objects
    channel, _ = channels.get_or_create(idx=cfg["idx"], defaults={"name": cfg["name"]})
    _, created = apps.get_model("django_pricemanager", "SaleChannel").objects.get_or_create(
        idx=cfg["idx"], channel=channel, defaults={"name": cfg["name"], "country": _country(cfg["country"])}
    )
    return _state(created)


def _regional_defaults(cfg: dict) -> dict:
    return {
        "label": cfg["name"],
        "default_language": _language(cfg["default_language"]),
        "default_currency": _currency(cfg["default_currency"]),
        "default_country": _country(cfg["country"]),
    }


def _checkout(cfg: dict) -> str:
    channels = apps.get_model("django_checkout", "Channel").objects
    _, created = channels.get_or_create(idx=cfg["idx"], defaults=_regional_defaults(cfg))
    return _state(created)


def _matrix(cfg: dict) -> str:
    channels = apps.get_model("django_matrix", "Channel").objects
    channel, created = channels.get_or_create(idx=cfg["idx"], defaults=_regional_defaults(cfg))
    if created:
        channel.languages.set(_languages(cfg))
        channel.currencies.set(_currencies(cfg))
        channel.countries.set([_country(cfg["country"])])
    return _state(created)


def _accounts(cfg: dict) -> str:
    defaults = {"label": cfg["name"], "language": _language(cfg["default_language"])}
    _, created = apps.get_model("django_accounts", "Channel").objects.get_or_create(idx=cfg["idx"], defaults=defaults)
    return _state(created)


def _qms(cfg: dict) -> str:
    defaults = {"name": cfg["name"]}
    if qms_type := getattr(settings, "QMS_TYPE", None):
        defaults["qms_type"] = qms_type
    _, created = apps.get_model("django_qms", "Channel").objects.get_or_create(idx=cfg["idx"], defaults=defaults)
    return _state(created)


def _show_key(key: str, kind: str) -> None:
    print(f"first-channel: storefront X-API-KEY {key} {kind}", flush=True)


def _access_token(idx: str) -> str:
    """An application token pinned to the channel; the raw value is printed once and cannot be read again."""
    listing, raw = io.StringIO(), io.StringIO()
    call_command("access_token", "list", "--application", STOREFRONT_APPLICATION, stdout=listing)
    if f"channel={idx}\t" in listing.getvalue():
        return EXISTS
    target = ["--application", STOREFRONT_APPLICATION, "--create-application"]
    grant = ["--scope", STOREFRONT_SCOPE, "--channel", idx, "--name", f"storefront {idx}"]
    call_command("access_token", "create", *target, *grant, stdout=raw, stderr=io.StringIO())
    _show_key(raw.getvalue().strip(), "access token")
    return CREATED


def _legacy_key(idx: str) -> str:
    keys = apps.get_model("django_checkout", "APIKey").objects.filter(channel__idx=idx)
    if keys.exists():
        return EXISTS
    call_command("generate-api-key", idx, stdout=io.StringIO())
    _show_key(keys.latest("created_at").key, "legacy key")
    return CREATED


def _api_key(cfg: dict) -> str:
    return _access_token(cfg["idx"]) if apps.is_installed("django_access") else _legacy_key(cfg["idx"])


def _admin(cfg: dict) -> str:
    """The Customer and verified EmailAddress rows the CMS login reads: createsuperuser does not create them."""
    from django.contrib.auth import get_user_model
    from django_accounts.receivers import create_staff_customer

    superusers = get_user_model().objects.filter(is_superuser=True)
    if not superusers.exists():
        return "skipped (no superuser: run createsuperuser, then this again)"
    missing = list(superusers.filter(customer__isnull=True))
    for user in missing:
        with transaction.atomic():  # both rows or neither: a half-made account would count as done next time
            create_staff_customer(sender=None, user=user)
    return _state(bool(missing))


def _munin(cfg: dict) -> str:
    call_command("discover_modules", stdout=io.StringIO())
    return RAN


STEPS = (
    ("regional", "django_regional", _regional),
    ("pim", "django_pim", _pim),
    ("sync", "django_pim", _sync),
    ("pricemanager", "django_pricemanager", _pricemanager),
    ("checkout", "django_checkout", _checkout),
    ("matrix", "django_matrix", _matrix),
    ("accounts", "django_accounts", _accounts),
    ("qms", "django_qms", _qms),
    ("api-key", "django_checkout", _api_key),
    ("admin", "django_accounts", _admin),
    ("munin", "django_munin", _munin),
)


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: python scripts/first_channel.py <config.toml>")
    try:
        cfg = load_config(sys.argv[1])
    except (OSError, ValueError) as exc:
        sys.exit(f"first-channel: {exc}")
    sys.path.insert(0, str(BASE_DIR))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings")
    django.setup()
    for step, app, run in STEPS:
        _report(step, run(cfg) if apps.is_installed(app) else f"skipped ({app} not enabled)")
    _report("done", cfg["idx"])


if __name__ == "__main__":
    main()
