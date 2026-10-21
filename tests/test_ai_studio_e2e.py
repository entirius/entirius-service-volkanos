# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""AI studio end to end through the installed apps (enrichment, PIM, ContentDB) on a mocked toolbox.

1. The product writer (template `meta`) with `seo_brief` on PIM products: proposals per field × language with
   costs, the brief remembered for the category and reused by a second product, a QA warning for a number that
   is not in the facts registry.
2. The correction loop: revise (edits), restore, a rule promoted into a memory suggestion, then into the
   profile — the next correction uses the new profile version.
3. The article workflow: brief → search phrases → questions → insights → outline → draft (section by section) → voice →
   edit (one correction) → metadata → document → an unpublished ContentDB blog-post draft.

The toolbox is `mock_toolbox` (respx): scripted completions picked by the selector tag and SEO answers with
costs. No real AI or DataForSEO call leaves the process.
"""

import base64
import importlib.util
import json
import re
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from django.conf import settings

ENRICHMENT = "django_enrichment" in settings.INSTALLED_APPS
# Workflows, profile and augmentations ship with the enrichment release of contracts A3/A4.
STUDIO = ENRICHMENT and importlib.util.find_spec("django_enrichment.augmentations") is not None
APPS = {"django_pim", "django_contentdb"} <= set(settings.INSTALLED_APPS)

pytestmark = [
    pytest.mark.skipif(not (STUDIO and APPS), reason="AI studio apps (enrichment A3/A4, PIM, ContentDB) not installed"),
    pytest.mark.django_db,
]

if STUDIO and APPS:
    from django_utils.toolbox.testing import CANNED_COMPLETION, mock_toolbox

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "common"
SEED_FILES = ("enrichment_workers.json", "article_workflow.json", "profile_demo.json")
CHANNEL = "studio-shop"
CATEGORY = "low-gravity-sofas"
SKUS = ("OF-SOFA-1", "OF-SOFA-2")
SEO = "http://toolbox.test/api/ai-seo/v2/admin/shop"
IMAGES = "http://toolbox.test/api/ai-media/v2/admin/shop/images"
IMAGE_JOB = "7a1c0d2e-0000-4000-8000-000000000000"
IMAGE_COST = "0.039"
# A 1×1 PNG: what every image job answers.
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M8AAAMBAQDJ/pLvAAAAAElFTkSuQmCC")
COMPLETION_COST = "0.002"
SEO_COST = "0.05"
UNKNOWN_NUMBER = "777"
TEXT_FEATURES = {"meta_title": "VARCHAR255_T9N", "meta_description": "VARCHAR255_T9N", "description": "TEXT_T9N"}

SEEDS = {"seeds": ["low gravity sofa", "station lounge sofa", "vacuum tested sofa"]}
BRIEF = {
    "primary": "low gravity sofa",
    "secondary": ["station lounge sofa"],
    "intent": "commercial",
    "serp_notes": "Shop category pages rank; guides do not.",
    "gaps": ["How the frame holds in 0.3 g"],
}
QUESTIONS = {
    "questions": [
        {
            "id": "audience",
            "question": "Who buys it?",
            "why": "Voice",
            "type": "text",
            "choices": [],
            "optional": False,
        },
        {
            "id": "tone",
            "question": "Tone?",
            "why": "Voice",
            "type": "choice",
            "choices": ["warm", "dry"],
            "optional": False,
        },
    ]
}
KEYWORDS = {
    **BRIEF,
    "candidates": [
        {"phrase": "low gravity sofa", "volume": 900, "intent": "commercial", "serp_notes": "Shops"},
        {"phrase": "station sofa care", "volume": 300, "intent": "informational", "serp_notes": "Guides"},
    ],
}
INSIGHTS = "# Insights\n\n## From the author\n\n- I1 (author: who buys it) Long-haul freighter crews."
OUTLINE = "# Sofas for low gravity\n\n### 1. Frame\n- material: I1\n\n### 2. Care\n- material: I1"
DRAFT = (
    "# Sofas for low gravity\n\n## Frame\n\nThe frame of every sofa passes 500 vacuum test cycles before it leaves "
    "the workshop, so the joints stay tight when the station gravity drops to 0.3 g. The upholstery is stitched "
    "with a double seam that keeps the cushions in place during docking manoeuvres.\n\n## Care\n\nBrush the "
    "fabric once a week and air the cushions after every long haul."
)
META = {
    "title": "Sofas for low gravity",
    "description": "How a sofa frame holds when the station gravity drops.",
    "og_title": "Sofas for low gravity",
    "og_description": "Frames tested for vacuum cycles.",
    "slug": "Sofas for Low Gravity",
    "faq": [{"question": "How do I clean it?", "answer": "Brush the fabric once a week."}],
}
META_TITLE = "Low gravity sofa for freighter crews and long hauls"  # 40-60 characters
META_DESCRIPTION = (  # 120-160 characters
    f"Rated for {UNKNOWN_NUMBER} docking cycles, this low gravity sofa keeps its cushions in place with a double seam. "
    "See the frame details and the care notes."
)
SHORTER = "Shorter sentences, please."
LONG_HTML = "<p>The frame passes 500 vacuum test cycles.</p><ul><li>Double seam</li></ul>" + "<p>Calm.</p>" * 30


# --- toolbox -------------------------------------------------------------------------------------------------


def _selector(request: httpx.Request) -> tuple[str, dict]:
    body = json.loads(request.content)
    return body["tags"][0], body["json_schema"].get("properties", {})


def _write_answer(properties: dict) -> dict:
    """One string per field, inside the seeded `field_limits` of `pim.writer` (a rewrite would add completions); the
    meta description carries a number the facts registry does not know."""
    texts = {"meta_title": META_TITLE, "meta_description": META_DESCRIPTION}
    return {key: texts.get(key, LONG_HTML) for key in properties}


def _revise_answer(properties: dict) -> dict:
    if "edits" in properties:
        return {"edits": [{"old": "seam", "new": "seam line"}], "rewrite": None}
    return {"text": "Sofa for low gravity"}


_STEP_ANSWERS = {
    "article.questions": QUESTIONS,
    "article.keywords": KEYWORDS,
    "article.insights": {"text": INSIGHTS},
    "article.outline": {"text": OUTLINE},
    "article.draft": {"text": DRAFT},
    "article.voice": {"text": DRAFT},
    "article.edit": {"text": DRAFT},
    "article.meta": META,
    "article.cover_brief": {
        "scenes": [
            {
                "title": "Docked lounge",
                "prompt": "A sofa in a freighter lounge, soft cabin light.",
                "alt": "A sofa aboard",
            },
            {"title": "Seam detail", "prompt": "A hand pressing a double seam line, close-up.", "alt": "A double seam"},
        ]
    },
}


def _parsed(selector: str, properties: dict) -> dict:
    if "lead" in properties:  # the draft's last call: lead and closing around the written sections
        return {"lead": "Freighter crews sit a lot.", "closing": "## Your lounge\n\nWhat does your lounge need?"}
    if selector.startswith("enrichment.seo_brief.seeds"):
        return SEEDS
    if selector.startswith("enrichment.seo_brief.evaluate"):
        return BRIEF
    if selector.startswith("enrichment.write"):
        return _write_answer(properties)
    if selector.startswith("enrichment.revise"):
        return _revise_answer(properties)
    return next(answer for step, answer in _STEP_ANSWERS.items() if selector.endswith(step))


SECTIONS = {1: "## Frame\n\nThe frame passes 500 vacuum test cycles.", 2: "## Care\n\nBrush the fabric weekly."}


def _section(request: httpx.Request) -> dict | None:
    """A draft call for one outline section answers with that section only."""
    match = re.search(r"Write section (\d+) of", json.loads(request.content)["messages"][-1]["content"])
    return {"text": SECTIONS[int(match.group(1))]} if match else None


def _complete(request: httpx.Request) -> httpx.Response:
    parsed = _section(request) or _parsed(*_selector(request))
    return httpx.Response(200, json={**CANNED_COMPLETION, "parsed": parsed, "cost": COMPLETION_COST})


def _seo_envelope(data: dict) -> httpx.Response:
    return httpx.Response(200, json={"data": data, "cost": SEO_COST, "cached": False})


def _serp(request: httpx.Request) -> httpx.Response:
    organic = [{"rank": 1, "url": "https://a.test/sofas", "domain": "a.test", "title": "Sofas", "snippet": "Shop"}]
    return _seo_envelope({"organic": organic, "people_also_ask": [], "ai_overview": False})


def _volumes(request: httpx.Request) -> httpx.Response:
    keywords = json.loads(request.content)["keywords"]
    items = [
        {"keyword": keyword, "search_volume": 100 * (i + 1), "competition": 0.3, "cpc": 1.0}
        for i, keyword in enumerate(keywords)
    ]
    return _seo_envelope({"items": items})


@pytest.fixture
def toolbox(settings, tmp_path):
    """The mocked toolbox: `complete`, the three SEO routes and the image job, each answering with a cost."""
    settings.AI_TOOLBOX_BASE_URL = "http://toolbox.test"
    settings.AI_TOOLBOX_API_KEY = "test-key"
    settings.AI_TOOLBOX_CHANNEL = "shop"
    settings.ENRICHMENT_STAGING_DIR = str(tmp_path / "staging")
    settings.MEDIA_ROOT = str(tmp_path / "media")
    settings.TMP_DIR = str(tmp_path / "tmp")
    with mock_toolbox() as router:
        done = {"job_id": IMAGE_JOB, "status": "done", "outputs": [{"index": 0}], "cost": IMAGE_COST}
        yield SimpleNamespace(
            complete=router["complete"].mock(side_effect=_complete),
            seo=[
                router.post(f"{SEO}/search-volume/").mock(side_effect=_volumes),
                router.post(f"{SEO}/keyword-ideas/").mock(side_effect=_volumes),
                router.post(f"{SEO}/serp/").mock(side_effect=_serp),
            ],
            images=router.post(f"{IMAGES}/").mock(
                return_value=httpx.Response(202, json={"job_id": IMAGE_JOB, "status": "pending"})
            ),
            image_job=router.get(f"{IMAGES}/{IMAGE_JOB}/").mock(return_value=httpx.Response(200, json=done)),
            image_file=router.get(f"{IMAGES}/{IMAGE_JOB}/outputs/0/download/").mock(
                return_value=httpx.Response(200, content=PNG)
            ),
        )


def _form(request: httpx.Request) -> dict[str, str]:
    """The text fields of a multipart image-job request."""
    fields = re.findall(rb'name="([^"]+)"\r\n\r\n(.*?)\r\n--', request.content, re.S)
    return {name.decode(): value.decode() for name, value in fields if name != b"image"}


def _seo_calls(toolbox) -> int:
    return sum(route.call_count for route in toolbox.seo)


def _selectors(toolbox) -> list[str]:
    return [json.loads(call.request.content)["tags"][0] for call in toolbox.complete.calls]


def _messages(call) -> dict[str, str]:
    """One completion call's message text per role: `system` = instructions, `user` = data (contract A4 § 2-3)."""
    messages = json.loads(call.request.content)["messages"]
    return {role: "\n".join(m["content"] for m in messages if m["role"] == role) for role in ("system", "user")}


def _calls(toolbox, selector: str) -> list[dict[str, str]]:
    """The messages of every generation call (corrections excluded) whose selector tag contains `selector`."""
    tags = ((call, json.loads(call.request.content)["tags"][0]) for call in toolbox.complete.calls)
    return [_messages(call) for call, tag in tags if selector in tag and not tag.startswith("enrichment.revise")]


def _in_data_only(text: str, calls: list[dict[str, str]]) -> bool:
    return bool(calls) and all(text in call["user"] and text not in call["system"] for call in calls)


def _last(toolbox) -> dict[str, str]:
    return _messages(toolbox.complete.calls[-1])


# --- environment ---------------------------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _celery_eager():
    from celery import current_app

    previous = (current_app.conf.task_always_eager, current_app.conf.task_eager_propagates)
    current_app.conf.task_always_eager = current_app.conf.task_eager_propagates = True
    yield
    current_app.conf.task_always_eager, current_app.conf.task_eager_propagates = previous


@pytest.fixture
def run_tasks(django_capture_on_commit_callbacks):
    """`with run_tasks():` — tasks spawned inside really run (on-commit callbacks executed, Celery eager)."""
    return lambda: django_capture_on_commit_callbacks(execute=True)


@pytest.fixture
def seeds(db):
    """The service seeds: product writer/tagger, the article workflow and the demo company profile."""
    from django.core.management import call_command

    call_command("loaddata", *(str(FIXTURES / name) for name in SEED_FILES), verbosity=0)


@pytest.fixture
def operator(db):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(username="studio-operator", password="pw", is_staff=True)  # noqa: S106


@pytest.fixture
def catalog(db):
    """A PIM channel (pl + en) with the description and SEO text features and two sofas in one category."""
    from django_pim import models as pim
    from django_regional.models import Currency, Language

    polish, _ = Language.objects.get_or_create(
        iso2="PL", defaults={"iso3": "POL", "name_en": "Polish", "name_pl": "Polski"}
    )
    english, _ = Language.objects.get_or_create(
        iso2="EN", defaults={"iso3": "ENG", "name_en": "English", "name_pl": "Angielski"}
    )
    currency, _ = Currency.objects.get_or_create(iso3="PLN", defaults={"name_en": "Zloty", "name_pl": "Złoty"})
    channel = pim.Channel.objects.create(
        idx=CHANNEL, name="Studio shop", default_language=polish, default_currency=currency
    )
    channel.languages.add(polish, english)
    feature_set = pim.FeatureSet.objects.create(idx="studio-sofas", name="Studio sofas")
    for idx, feature_type in TEXT_FEATURES.items():
        feature, _ = pim.Feature.objects.get_or_create(idx=idx, defaults=_system_feature(pim, idx, feature_type))
        pim.FeatureInFeatureSet.objects.create(feature_set=feature_set, feature=feature, position=1)
    category = pim.ProductCategory.objects.create(shop=channel, idx=CATEGORY, name_t9n={"en": "Low gravity sofas"})
    for sku in SKUS:
        real = pim.RealProduct.objects.create(sku=sku)
        product = pim.Product.objects.create(shop=channel, real_product=real, feature_set=feature_set)
        pim.ProductInCategory.objects.create(product=product, category=category, position=0)
    return channel


def _system_feature(pim, idx: str, feature_type: str) -> dict:
    """A system text feature as the PIM seeds create it."""
    return {
        "scope": pim.FeatureScopeEnum.SYSTEM,
        "feature_type": getattr(pim.FeatureTypeEnum, feature_type),
        "is_seo": idx.startswith("meta_"),
        "name_t9n": {"en": idx},
    }


def _write(run_tasks, operator, *, template: str, sku: str, params: dict | None = None):
    from django_enrichment.services import task_service

    scope = {"mode": "list", "module": "pim", "refs": [sku]}
    with run_tasks():
        task = task_service.spawn(
            type="",
            template=template,
            scope_spec=scope,
            params={"channel": CHANNEL, **(params or {})},
            requested_by=operator,
        )
    task.refresh_from_db()
    return task


def _proposals(task) -> dict[tuple[str, str], object]:
    return {(p.target_locator["feature_idx"], p.target_locator["language"]): p for p in task.proposals.all()}


class TestProductWriterWithSeo:
    """Template `meta` with `seo_brief` on two products of one category."""

    @pytest.fixture
    def first(self, seeds, catalog, toolbox, run_tasks, operator):
        return _write(run_tasks, operator, template="meta", sku=SKUS[0], params={"augment": ["seo_brief"]})

    def test_proposals_per_field_and_language_with_costs(self, first):
        proposals = _proposals(first)
        assert set(proposals) == {(f, lang) for f in ("meta_title", "meta_description") for lang in ("pl", "en")}
        assert {p.status for p in proposals.values()} == {"pending"}
        assert {p.cost_usd for p in proposals.values()} == {Decimal(COMPLETION_COST) / 2}
        # per language: seeds + evaluate + write completions; search volume, ideas and 3 SERPs
        breakdown = {source: Decimal(cost) for source, cost in first.cost_breakdown.items()}
        assert breakdown == {"completion": 6 * Decimal(COMPLETION_COST), "seo": 10 * Decimal(SEO_COST)}
        assert (first.cost_usd, first.cost_complete) == (sum(breakdown.values()), True)

    def test_seo_brief_is_remembered_for_the_category_per_language(self, first, toolbox):
        from django_enrichment.models import MemoryEntry

        briefs = MemoryEntry.objects.filter(kind="seo_brief")
        assert {(b.subject_ref, b.data["language"], b.data["primary"]) for b in briefs} == {
            (f"category:{CATEGORY}", "pl", "low gravity sofa"),
            (f"category:{CATEGORY}", "en", "low gravity sofa"),
        }
        assert {b.source for b in briefs} == {f"task:{first.pk}"}

    def test_the_brief_and_the_serp_reach_the_prompts_as_data_never_as_instructions(self, first, toolbox):
        assert _in_data_only("Primary phrase: low gravity sofa", _calls(toolbox, "enrichment.write"))
        assert _in_data_only("Sofas", _calls(toolbox, "enrichment.seo_brief.evaluate"))
        assert all("Orbital Foundry" in call["system"] for call in _calls(toolbox, "enrichment.write"))

    def test_a_second_product_of_the_category_reuses_the_brief(self, first, toolbox, run_tasks, operator):
        seo_calls, completions = _seo_calls(toolbox), toolbox.complete.call_count
        second = _write(run_tasks, operator, template="meta", sku=SKUS[1], params={"augment": ["seo_brief"]})
        assert _seo_calls(toolbox) == seo_calls
        assert _selectors(toolbox)[completions:] == ["enrichment.write.meta"] * 2
        assert second.cost_breakdown.get("seo") is None
        assert len(_proposals(second)) == 4

    def test_a_number_outside_the_facts_is_a_qa_warning(self, first):
        description = _proposals(first)[("meta_description", "en")]
        title = _proposals(first)[("meta_title", "en")]
        assert [(w["code"], w["span"]["text"]) for w in description.warnings] == [
            ("NUMBER_NOT_IN_FACTS", UNKNOWN_NUMBER)
        ]
        assert title.warnings == []
        assert description.revisions.get().warnings == description.warnings


LIMITS = ENRICHMENT and importlib.util.find_spec("django_enrichment.kinds.field_limits") is not None


@pytest.mark.skipif(not LIMITS, reason="enrichment with `field_limits` (kind write length ranges) not installed")
class TestProductWriterLengthLimits:
    """The seeded `pim.writer` keeps meta fields inside its `field_limits` through the real PIM adapter."""

    TOO_LONG = "L" * 195

    def _run(self, toolbox, run_tasks, operator, rewritten: str):
        def answer(parsed: dict) -> httpx.Response:
            return httpx.Response(200, json={**CANNED_COMPLETION, "parsed": parsed, "cost": COMPLETION_COST})

        toolbox.complete.mock(
            side_effect=[
                answer({"meta_title": META_TITLE, "meta_description": self.TOO_LONG}),
                answer({"meta_description": rewritten}),
            ]
        )
        return _write(run_tasks, operator, template="meta", sku=SKUS[0], params={"languages": ["en"]})

    @pytest.fixture(autouse=True)
    def _env(self, seeds, catalog):
        pass

    def test_a_description_over_the_limit_is_rewritten_once(self, toolbox, run_tasks, operator):
        task = self._run(toolbox, run_tasks, operator, rewritten=META_DESCRIPTION)
        description = _proposals(task)[("meta_description", "en")]
        assert _selectors(toolbox) == ["enrichment.write.meta"] * 2
        assert description.proposed_value == {"text": META_DESCRIPTION}
        assert [w["code"] for w in description.warnings] == ["NUMBER_NOT_IN_FACTS"]  # the mock's number, no LIMIT
        assert task.cost_usd == 2 * Decimal(COMPLETION_COST)

    def test_a_rewrite_that_missed_stays_and_review_sees_the_limit(self, toolbox, run_tasks, operator):
        task = self._run(toolbox, run_tasks, operator, rewritten="M" * 170)
        description = _proposals(task)[("meta_description", "en")]
        assert toolbox.complete.call_count == 2
        assert description.proposed_value == {"text": "M" * 170}
        assert [(w["code"], w["message"]) for w in description.warnings] == [
            ("LIMIT", "170 characters, the limit is 160.")
        ]
        assert _proposals(task)[("meta_title", "en")].warnings == []


class TestCorrectionLoop:
    """Revise, restore, promote a rule into the profile; the next correction uses the new profile version."""

    RULE = "Name the vacuum test in the first sentence."

    @pytest.fixture
    def proposal(self, seeds, catalog, toolbox, run_tasks, operator):
        task = _write(run_tasks, operator, template="description", sku=SKUS[0], params={"languages": ["en"]})
        return _proposals(task)[("description", "en")]

    def test_revise_applies_the_edits_and_restore_brings_back_the_first_version(self, proposal, operator):
        from django_enrichment.services import revise_service, revision_service

        revised = revise_service.revise(proposal, instruction=SHORTER, user=operator)
        assert (revised.number, revised.author_kind, revised.instruction) == (2, "ai", SHORTER)
        assert "Double seam line" in revised.value["text"]
        assert revised.cost_usd == Decimal(COMPLETION_COST)
        restored = revision_service.restore(proposal, 1, user=operator)
        proposal.refresh_from_db()
        assert (restored.number, restored.author_kind) == (3, "restore")
        assert proposal.proposed_value == restored.value == proposal.revisions.get(number=1).value

    def test_a_promoted_rule_reaches_the_next_correction_through_a_new_profile_version(
        self, proposal, operator, toolbox
    ):
        from django_enrichment.models import MemoryEntry
        from django_enrichment.services import (
            memory_promotion,
            profile_service,
            revise_service,
            revision_service,
            rules_service,
        )

        before = revise_service.revise(proposal, instruction=SHORTER, user=operator)
        revision_service.restore(proposal, 1, user=operator)
        rules_service.promote(proposal, self.RULE, target="profile")
        suggestion = MemoryEntry.objects.get(kind="rule_suggestion")
        assert (suggestion.text, suggestion.status, suggestion.source) == (
            self.RULE,
            "active",
            f"proposal:{proposal.pk}",
        )
        assert self.RULE not in "\n".join(_last(toolbox).values())

        profile = memory_promotion.promote(suggestion, user=operator)
        suggestion.refresh_from_db()
        assert suggestion.status == "promoted"
        assert self.RULE in profile.data["always_rules"]
        after = revise_service.revise(proposal, instruction=SHORTER, user=operator)
        assert after.profile_versions == profile_service.version_ids(CHANNEL) != before.profile_versions
        assert (self.RULE in _last(toolbox)["system"], self.RULE in _last(toolbox)["user"]) == (True, False)

    def test_promotion_keeps_the_instance_always_rules(self, proposal, operator):
        from django_enrichment.models import MemoryEntry
        from django_enrichment.services import memory_promotion, profile_service, rules_service

        instance_rules = profile_service.get_profile().data["always_rules"]
        rules_service.promote(proposal, self.RULE, target="profile")
        memory_promotion.promote(MemoryEntry.objects.get(kind="rule_suggestion"), user=operator)
        assert profile_service.merged(CHANNEL)["always_rules"] == [*instance_rules, self.RULE]


# --- article workflow ----------------------------------------------------------------------------------------

BRIEF_INPUTS = {
    "topic": "Sofas for low gravity",
    "language": "en",
    "audience": "Freighter crews",
    "cover_hint": "Warm cabin light, no stars",
}
ANSWERS = {"audience": "Crews on long-haul freighters", "tone": "warm"}
PICKED = {**KEYWORDS, "secondary": ["station sofa care"]}
STEPS = (
    "keywords",
    "questions",
    "insights",
    "outline",
    "draft",
    "voice",
    "edit",
    "meta",
    "cover_brief",
    "cover",
    "compose",
)


@pytest.fixture
def blog(db):
    """The ContentDB side: an English `web` channel and the blog-post content type the document step creates."""
    from django_contentdb.models import AttributeSet, ContentChannel, ContentType, Language

    english = Language.objects.create(iso2="EN", iso3="ENG")
    ContentChannel.objects.create(idx="web", default_language=english, is_default=True)
    ContentType.objects.create(
        slug="blog-post", label="Blog post", attribute_set=AttributeSet.objects.create(label="Blog")
    )


def _step_proposal(uid: str, key: str):
    from django_enrichment.models import ContentProposal
    from django_enrichment.services import workflow_queries

    state = next(s for s in workflow_queries.get_run(uid).steps_state if s["key"] == key)
    return ContentProposal.objects.get(pk=state["proposal_id"])


def _approve(run_tasks, uid: str, key: str, operator, value: dict | None = None):
    from django_enrichment.services import proposal_service

    proposal = _step_proposal(uid, key)
    if value is not None:
        proposal_service.update_value(proposal, value, user=operator)
    with run_tasks():
        proposal_service.accept(proposal, user=operator)


@pytest.fixture
def article(seeds, blog, toolbox, run_tasks, operator):
    """The article run driven to its end: a phrase pick, answers, one edit correction, every step approved."""
    from django_enrichment.services import revise_service, workflow_queries, workflow_service

    with run_tasks():
        uid = workflow_service.start(definition="article", inputs=BRIEF_INPUTS, channel="web", user=operator).uid
    _approve(run_tasks, uid, "keywords", operator, {"data": PICKED})
    questions = _step_proposal(uid, "questions").proposed_value
    _approve(run_tasks, uid, "questions", operator, {**questions, "answers": ANSWERS})
    for key in ("insights", "outline", "draft", "voice"):
        _approve(run_tasks, uid, key, operator)
    revise_service.revise(_step_proposal(uid, "edit"), instruction=SHORTER, user=operator)
    for key in ("edit", "meta", "cover_brief"):
        _approve(run_tasks, uid, key, operator)
    cover = _step_proposal(uid, "cover").proposed_value
    _approve(run_tasks, uid, "cover", operator, {**cover, "chosen": 1, "alt": "A double seam line, close-up"})
    _approve(run_tasks, uid, "compose", operator)
    return workflow_queries.get_run(uid)


class TestArticleWorkflow:
    def test_every_step_is_approved_and_the_run_is_done(self, article):
        assert [(s["key"], s["status"]) for s in article.steps_state] == [(key, "approved") for key in STEPS]
        assert article.status == "done"

    def test_the_document_is_an_unpublished_blog_post_draft(self, article):
        from django_contentdb.models import Content

        content = Content.objects.get(uid=article.subject_ref)
        draft = content.draft
        sections = [content.content["sections"][uid] for uid in content.content["sections_order"]]
        assert (draft.content_type.slug, draft.published.exists()) == ("blog-post", False)
        assert list(draft.channels.values_list("idx", flat=True)) == ["web"]
        assert list(draft.routes.values_list("url", flat=True)) == ["sofas-for-low-gravity"]
        assert {"section-text", "section-faq"} <= {section["core_type"] for section in sections}
        assert content.meta["title"] == META["title"]
        assert "seam line" in json.dumps(content.content)

    def test_the_picked_cover_is_the_blog_tile_image_and_the_og_image(self, article, toolbox):
        from django_contentdb.models import Content, Image

        content = Content.objects.get(uid=article.subject_ref)
        image = Image.objects.get(uid=content.extension["images_set"]["desktop"]["uid"])
        assert image.meta["alt"] == "A double seam line, close-up"
        assert content.meta["og_image"] == image.image.url
        prompts = [_form(call.request)["prompt"] for call in toolbox.images.calls]
        assert len(prompts) == 2 and "A hand pressing a double seam line" in prompts[1]
        assert all("No text, letters" in prompt for prompt in prompts)

    def test_the_cover_hints_reach_only_the_cover_scenes(self, article, toolbox):
        assert _in_data_only("Warm cabin light", _calls(toolbox, "article.cover_brief"))
        others = [
            call for call in toolbox.complete.calls if "cover_brief" not in json.loads(call.request.content)["tags"][0]
        ]
        assert others and all("Warm cabin light" not in call.request.content.decode() for call in others)

    def test_run_cost_is_the_sum_of_its_tasks(self, article):
        from django_enrichment.models import EnrichmentTask

        tasks = EnrichmentTask.objects.filter(params__run=article.uid)
        assert tasks.count() == len(STEPS)
        known = [task.cost_usd for task in tasks if task.cost_usd is not None]  # compose calls no toolbox
        assert article.cost_usd == sum(known, Decimal(0)) > 0
        keywords = tasks.get(params__template="article.keywords")
        assert Decimal(keywords.cost_breakdown["seo"]) > 0

    def test_answers_and_the_phrase_pick_feed_the_later_steps(self, article):
        from django_enrichment.models import EnrichmentTask, MemoryEntry

        answers = MemoryEntry.objects.filter(kind="answer").order_by("pk")
        assert [(a.title, a.text) for a in answers] == [("Who buys it?", ANSWERS["audience"]), ("Tone?", "warm")]
        assert {a.source for a in answers} == {f"run:{article.uid}/questions"}
        outline = EnrichmentTask.objects.get(params__run=article.uid, params__template="article.outline")
        assert outline.params["inputs"]["keywords"] == {"data": PICKED}

    def test_the_answers_reach_the_writing_prompts_as_data(self, article, toolbox):
        for step in ("article.insights", "article.outline", "article.draft", "article.voice"):
            assert _in_data_only(ANSWERS["audience"], _calls(toolbox, step)), step

    def test_questions_and_insights_see_the_search_evidence_of_the_keywords_step(self, article, toolbox):
        steps = ("generate.article.keywords", "questions.article.questions", "generate.article.insights")
        for step in steps:
            assert _in_data_only('SERP "low gravity sofa"', _calls(toolbox, f"enrichment.{step}")), step

    def test_the_research_runs_once_for_the_whole_run(self, article):
        from django_enrichment.models import EnrichmentTask

        tasks = EnrichmentTask.objects.filter(params__run=article.uid)
        assert [task.params["template"] for task in tasks if "seo" in (task.cost_breakdown or {})] == [
            "article.keywords"
        ]

    def test_the_questions_need_at_least_one_answer(self, article):
        assert _step_proposal(article.uid, "questions").proposed_value["min_answers"] == 1

    def test_a_section_is_written_from_the_insights_its_outline_block_assigns(self, article, toolbox):
        sections = [c for c in _calls(toolbox, "enrichment.sections.article.draft") if "Write section" in c["user"]]
        assert all("- material: I1" in call["user"] for call in sections)
        assert _in_data_only("I1 (author: who buys it)", sections)

    def test_the_draft_is_written_section_by_section_then_its_lead_and_closing(self, article, toolbox):
        assert len(_calls(toolbox, "enrichment.sections.article.draft")) == 3  # two outline sections + the ends
        text = _step_proposal(article.uid, "draft").proposed_value["text"]
        assert text.startswith("Freighter crews sit a lot.") and text.endswith(
            "## Your lounge\n\nWhat does your lounge need?"
        )
        assert text.count("## Frame") == 1 and "## Care" in text

    def test_the_edit_correction_is_a_revision_of_the_document_body(self, article):
        edit = _step_proposal(article.uid, "edit")
        assert [(r.number, r.author_kind) for r in edit.revisions.order_by("number")] == [(1, "ai"), (2, "ai")]
        assert edit.status == "applied" and "double seam line" in edit.proposed_value["text"]
