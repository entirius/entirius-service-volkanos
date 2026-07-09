# AGENTS.md

Volkanos — base Django service of the Entirius platform: a thin Django + DRF shell
orchestrating `entirius-py-*` / `entirius-django-*` modules.
Currently **Stage 0**: clean skeleton, no business modules.

## What this service is

Modules **do not live in this repo** — each is its own repo, installed as a dependency.
Adopting an `entirius-django-*` module = dependency in `pyproject.toml` (+ `uv lock`),
its app in `LOCAL_APPS` (`main/settings.py`), `include()` of its urls in `main/urls.py`.
Plain `entirius-py-*` libraries are dependencies only — no `LOCAL_APPS` / urls wiring.
Adopting a module does not change its name / app_label / DB tables.

## Stack and tooling

- Django 5.2+ / DRF / drf-spectacular (OpenAPI)
- uv (packages), ruff (lint + format), hatchling (build), pytest
- DB: `DATABASE_URL` env var (postgres under entirius-zeno / CI); sqlite fallback
- Per-environment config: `main/settings_local.py` (gitignored) - REQUIRED, service refuses to boot
  without it; template: `main/settings_example.py`; must define ENVIRONMENT, SECRET_KEY, DATABASES

## Commands

| Command | Meaning |
|---|---|
| `make install` | sync dependencies (uv) |
| `make check` / `make fix` | lint + format (ruff) |
| `make test` | migration drift check + pytest |
| `make run` / `migrate` / `makemigrations` / `shell` / `schema` | Django dev tasks |
| `make health` | prod-safe read-only health check |
| `make init` / `recreate-db` / `reinstall` / `rebuild` / `test-users` | dev-only, fail-closed on `ENVIRONMENT` |

Dev-only tasks require `ENVIRONMENT=development` in `.env` — they refuse to run otherwise.
One-time: `uv run pre-commit install` (git hooks: ruff + MPL license header + gitleaks).

## Conventions

- English only: code, docs, commits, branches, PRs.
- MPL-2.0: every non-trivial source file carries the license header (pre-commit inserts it, CI enforces).
- Dependencies only in `pyproject.toml` (+ `uv.lock` committed); no `requirements.txt` / `setup.py`.
- Git flow: `master` (production) + `develop` (integration); changes land via PR.
- Default: do not commit — git is the user's call.
