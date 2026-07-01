# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Readiness smoke — Django config coheres and the DB builds from migrations."""

import pytest
from django.core.management import call_command
from django.db import connection


def test_system_check_passes():
    """Settings load, apps boot, urls import, DRF wiring is coherent."""
    call_command("check")


@pytest.mark.django_db
def test_database_ready():
    """Throwaway DB builds from all migrations and answers a live query."""
    with connection.cursor() as cur:
        cur.execute("SELECT 1")
        assert cur.fetchone()[0] == 1
