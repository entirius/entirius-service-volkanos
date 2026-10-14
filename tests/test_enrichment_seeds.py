# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The AI studio seeds (`fixtures/common/`): demo profile, product writer/tagger, article workflow.

They load into a fresh database and pass the same validation as an edit in Django admin or the profile API.
"""

import importlib.util
import json
from pathlib import Path

import pytest
from django.conf import settings

ENRICHMENT = "django_enrichment" in settings.INSTALLED_APPS
# The seeds need the enrichment release with contract A3/A4 (profile schema, templates, workflows);
# the service lock pins an older one until that release ships.
PROFILE_SCHEMA = ENRICHMENT and importlib.util.find_spec("django_enrichment.schemas.profile") is not None

pytestmark = pytest.mark.skipif(
    not PROFILE_SCHEMA, reason="django_enrichment with the profile schema (contract A3/A4) not in INSTALLED_APPS"
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "common"
SEEDS = ["enrichment_workers.json", "article_workflow.json", "profile_demo.json"]


def _rows(name: str) -> list[dict]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _profile_data() -> dict:
    return next(row for row in _rows("profile_demo.json") if row["model"] == "django_enrichment.profile")["fields"][
        "data"
    ]


def test_demo_profile_matches_the_profile_schema():
    from django_enrichment.schemas.profile import validation_errors

    assert validation_errors(_profile_data()) == []


def test_demo_profile_version_snapshots_the_profile():
    version = next(row for row in _rows("profile_demo.json") if row["model"] == "django_enrichment.profileversion")

    assert version["fields"]["data"] == _profile_data()


def test_unverified_facts_are_held_back_by_an_always_rule():
    data = _profile_data()

    assert any(not fact["verified_at"] for fact in data["facts"])
    assert any("verified_at" in rule for rule in data["always_rules"])


def test_demo_profile_routes_seeded_workers_only():
    worker_keys = {row["fields"]["key"] for name in SEEDS[:2] for row in _rows(name) if row["model"].endswith("worker")}

    assert set(_profile_data()["routing"]) <= worker_keys


def test_every_seeded_worker_uses_the_channel_default_model():
    workers = [row["fields"] for name in SEEDS[:2] for row in _rows(name) if row["model"].endswith("worker")]

    assert {worker["model"] for worker in workers} == {""}


@pytest.mark.django_db
def test_seeds_load_and_pass_model_validation():
    from django.core.management import call_command
    from django_enrichment.models import TaskTemplate, Worker, WorkflowDefinition
    from django_enrichment.services import profile_service

    call_command("loaddata", *(str(FIXTURES / name) for name in SEEDS), verbosity=0)

    for model in (Worker, TaskTemplate, WorkflowDefinition):
        for row in model.objects.all():
            row.full_clean()
    assert set(Worker.objects.filter(kind="field").values_list("active", flat=True)) == {False}
    assert profile_service.status("")["complete"]
