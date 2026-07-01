# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Create configured test users on non-production environments (idempotent).

Users come from scripts/test_users.yaml (gitignored, local override) or, if absent,
scripts/test_users.example.yaml (committed template). Run via `make test-users` / `make init`.
Refused unless ENVIRONMENT is a dev environment (fail-closed, defense-in-depth over guard-dev).
"""

import os
import sys
from pathlib import Path

import django
import yaml
from django.conf import settings

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
LOCAL_CONFIG = SCRIPT_DIR / "test_users.yaml"
EXAMPLE_CONFIG = SCRIPT_DIR / "test_users.example.yaml"
ALLOWED_ENVIRONMENTS = {"development", "local"}


def main() -> None:
    sys.path.insert(0, str(BASE_DIR))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings")
    django.setup()

    if settings.ENVIRONMENT not in ALLOWED_ENVIRONMENTS:
        sys.exit(
            f"REFUSED: ENVIRONMENT={settings.ENVIRONMENT!r} is not a dev environment."
        )

    config = LOCAL_CONFIG if LOCAL_CONFIG.exists() else EXAMPLE_CONFIG
    if config is EXAMPLE_CONFIG:
        print(f"  (using {config.name} — copy to test_users.yaml to customize)")

    from django.contrib.auth import get_user_model

    user_model = get_user_model()
    for spec in yaml.safe_load(config.read_text())["users"]:
        _ensure_user(user_model, spec)


def _ensure_user(user_model, spec: dict) -> None:
    user, created = user_model.objects.get_or_create(
        username=spec["username"],
        defaults={"email": spec.get("email", "")},
    )
    user.email = spec.get("email", user.email)
    user.is_superuser = spec.get("superuser", False)
    user.is_staff = spec.get("staff", False) or user.is_superuser
    user.set_password(spec["password"])
    user.save()
    print(f"  {'created' if created else 'updated'}: {user.username}")


if __name__ == "__main__":
    main()
