# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""modules.yaml stays true against pyproject.toml, main/urls.py, main/settings.py and the installed package metadata.

No Django import: the file runs with ``-p no:django`` in a venv synced from the lock.
"""

import importlib.metadata
import importlib.util
import json
import re
import tomllib
from pathlib import Path

import pytest
import yaml
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = yaml.safe_load((ROOT / "modules.yaml").read_text())
MODULES, PLATFORM, LIBRARIES = REGISTRY["modules"], REGISTRY["platform"], REGISTRY["libraries"]
MODULE_PREFIX, LIBRARY_PREFIX = "entirius-django-", "entirius-py-"
DOMAINS = [
    "foundation",
    "catalog",
    "pricing-stock",
    "orders",
    "content",
    "customers",
    "suppliers",
    "leads",
    "integrations",
]
MODULE_CATEGORIES = {"magento", "marketing", "service"}
LIBRARY_CATEGORIES = {"payment", "magento", "marketing", "service", "utility"}
NON_RUNTIME_EXTRAS = {"test", "dev"}
URL_GUARD = re.compile(
    r'^if "(\w+)" in settings\.INSTALLED_APPS:\n    urlpatterns\.append\(path\("", include\("\1\.urls"\)\)\)$',
    re.MULTILINE,
)
EXTRA = re.compile(r"""extra\s*==\s*["']([^"']+)["']""")


def _dependencies(prefix: str) -> set[str]:
    with (ROOT / "pyproject.toml").open("rb") as pyproject:
        requirements = tomllib.load(pyproject)["project"]["dependencies"]
    names = {canonicalize_name(Requirement(requirement).name) for requirement in requirements}
    return {name for name in names if name.startswith(prefix)}


def _dists(entries: list[dict]) -> list[str]:
    return [entry["dist"] for entry in entries]


def _metadata_skip_reason(entry: dict) -> str | None:
    """Why the installed metadata of ``entry`` cannot be compared, or None when it can."""
    try:
        dist = importlib.metadata.distribution(entry["dist"])
    except importlib.metadata.PackageNotFoundError:
        if entry in PLATFORM:
            return f"{entry['dist']} is not installed in this environment"
        raise
    direct_url = json.loads(dist.read_text("direct_url.json") or "{}")
    if direct_url.get("dir_info", {}).get("editable"):
        return f"{entry['dist']} is installed editable: its metadata is the local clone's, not the lock's"
    return None


def _requirements(dist: str, prefix: str) -> list[tuple[str, set[str]]]:
    """``(name, extras that pull it)`` for every requirement of ``dist`` whose name starts with ``prefix``."""
    parsed = [Requirement(requirement) for requirement in importlib.metadata.requires(dist) or []]
    pairs = [(canonicalize_name(req.name), set(EXTRA.findall(str(req.marker or "")))) for req in parsed]
    return [(name, extras) for name, extras in pairs if name.startswith(prefix)]


def test_modules_are_the_django_dependencies():
    dists = _dists(MODULES)
    assert len(dists) == len(set(dists))
    assert set(dists) == _dependencies(MODULE_PREFIX) - set(_dists(PLATFORM))


def test_platform_apps_are_installed_by_the_service():
    settings_source = (ROOT / "main" / "settings.py").read_text()
    for app in (app for entry in PLATFORM for app in entry["apps"]):
        assert f'find_spec("{app}")' in settings_source


def test_direct_libraries_are_the_py_dependencies():
    direct = [library["dist"] for library in LIBRARIES if "via" not in library]
    assert len(direct) == len(set(direct))
    assert set(direct) == _dependencies(LIBRARY_PREFIX)


@pytest.mark.parametrize("library", [lib for lib in LIBRARIES if "via" in lib], ids=lambda lib: lib["dist"])
def test_via_library_is_a_requirement_of_its_module(library: dict):
    module_dist = library["via"].partition("[")[0]
    module = next(entry for entry in MODULES + PLATFORM if entry["dist"] == module_dist)
    if reason := _metadata_skip_reason(module):
        pytest.skip(reason)
    assert library["dist"] in [name for name, _ in _requirements(module_dist, LIBRARY_PREFIX)]


def test_urls_flag_matches_the_url_guards():
    guarded = set(URL_GUARD.findall((ROOT / "main" / "urls.py").read_text()))
    flagged = {app for entry in MODULES + PLATFORM if entry["urls"] for app in entry["apps"]}
    assert flagged == guarded


@pytest.mark.parametrize("entry", MODULES + PLATFORM, ids=lambda entry: entry["dist"])
def test_requires_and_optional_match_the_package_metadata(entry: dict):
    if reason := _metadata_skip_reason(entry):
        pytest.skip(reason)
    requirements = _requirements(entry["dist"], MODULE_PREFIX)
    assert sorted(entry["requires"]) == sorted({name for name, extras in requirements if not extras})
    assert sorted(entry["optional"]) == sorted({name for name, extras in requirements if extras - NON_RUNTIME_EXTRAS})


def test_requires_come_earlier_in_the_registry():
    seen: set[str] = set()
    for module in MODULES:
        assert set(module["requires"]) <= seen, module["dist"]
        seen.add(module["dist"])


def test_also_enable_names_known_apps():
    known = {app for module in MODULES for app in module["apps"]}
    for module in MODULES + PLATFORM:
        assert set(module["also_enable"]) <= known, module["dist"]


def test_domains_and_categories_are_from_the_lists():
    assert [domain["id"] for domain in REGISTRY["domains"]] == DOMAINS
    for entry in MODULES + PLATFORM:
        assert entry["domain"] in DOMAINS, entry["dist"]
        assert ("category" in entry) == (entry["domain"] == "integrations"), entry["dist"]
        assert entry.get("category", "service") in MODULE_CATEGORIES, entry["dist"]
    for library in LIBRARIES:
        assert library["category"] in LIBRARY_CATEGORIES, library["dist"]


def test_settings_example_is_rendered_from_the_registry():
    spec = importlib.util.spec_from_file_location(
        "render_settings_example", ROOT / "scripts/render_settings_example.py"
    )
    renderer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(renderer)
    current = renderer.EXAMPLE.read_text()
    assert renderer.render(current, REGISTRY) == current
