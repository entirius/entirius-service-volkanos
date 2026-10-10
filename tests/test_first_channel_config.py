# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The config loader of scripts/first_channel.py. No Django setup: the file runs with ``-p no:django``."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "scripts/first-channel.example.toml"
KEYS = {"idx", "name", "default_language", "languages", "default_currency", "currencies", "country"}


def _load_config():
    spec = importlib.util.spec_from_file_location("first_channel", ROOT / "scripts/first_channel.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.load_config


def test_example_config_has_the_seven_keys():
    config = _load_config()(EXAMPLE)

    assert set(config) == KEYS
    assert config["idx"] == "web"


def test_missing_idx_is_named(tmp_path):
    incomplete = tmp_path / "channel.toml"
    incomplete.write_text(EXAMPLE.read_text().replace('idx = "web"\n', ""))

    with pytest.raises(ValueError, match="idx"):
        _load_config()(incomplete)
