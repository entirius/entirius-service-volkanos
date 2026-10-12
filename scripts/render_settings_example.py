# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Render the commented module list of main/settings_example.py from modules.yaml.

Usage: python scripts/render_settings_example.py [--check]
"""

import argparse
import difflib
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "modules.yaml"
EXAMPLE = ROOT / "main" / "settings_example.py"
BEGIN = "# BEGIN generated from modules.yaml (make settings-example)"
END = "# END generated"
ACCESS_NOTE = "# django_access is added by main/settings.py in every environment (a required dependency)"


def _block(registry: dict) -> str:
    apps = [app for module in registry["modules"] for app in module["apps"]]
    return "\n".join(["# LOCAL_APPS = [", *(f'#     "{app}",' for app in apps), "# ]", ACCESS_NOTE])


def render(text: str, registry: dict) -> str:
    """Return ``text`` with the generated block replaced by the registry's apps, in registry order."""
    head, begin, rest = text.partition(BEGIN)
    _, end, tail = rest.partition(END)
    if not (begin and end):
        raise ValueError(f"markers not found: {BEGIN!r} ... {END!r}")
    return f"{head}{BEGIN}\n{_block(registry)}\n{END}{tail}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 with a diff when the file is stale")
    args = parser.parse_args(argv)
    current = EXAMPLE.read_text()
    rendered = render(current, yaml.safe_load(REGISTRY.read_text()))
    if not args.check:
        EXAMPLE.write_text(rendered)
        return 0
    diff = difflib.unified_diff(current.splitlines(True), rendered.splitlines(True), "current", "rendered")
    sys.stdout.writelines(diff)
    return int(rendered != current)


if __name__ == "__main__":
    sys.exit(main())
