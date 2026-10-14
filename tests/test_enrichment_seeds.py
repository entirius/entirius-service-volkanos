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

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("django_enrichment") is None, reason="django_enrichment is not installed"
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
