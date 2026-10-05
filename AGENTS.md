# AGENTS.md

Volkanos — base Django service of the Entirius platform: a thin Django + DRF shell
orchestrating `entirius-py-*` / `entirius-django-*` modules.

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

## Security settings (settings_local)

Defaults live in `main/settings.py`; values that feed DRF / drf-spectacular are applied after the settings_local import.

| Setting | Default | Meaning |
|---|---|---|
| `DRF_NUM_PROXIES` | `None` | trusted `X-Forwarded-For` hops for per-IP throttles; `1` behind Cloudflare → Caddy → nginx; unset with `DEBUG=False` → `volkanos.W001` |
| `API_SCHEMA_PUBLIC` | `False` | `True` serves `api/schema/`, swagger-ui and redoc anonymously; otherwise staff only |
| `AUTH_TOKEN_FAILURE_WINDOW_S` | `900` | window of the failed-login counters on `api/token/` (read by `django_access.services.login_guard`; no access, no counter) |
| `AUTH_TOKEN_MAX_FAILURES_PER_USER_IP` | `10` | failures per username + address before 429 |
| `AUTH_TOKEN_MAX_FAILURES_PER_IP` | `100` | failures per address before 429 |

## Conventions

- English only: code, docs, commits, branches, PRs.
- MPL-2.0: every non-trivial source file carries the license header (pre-commit inserts it, CI enforces).
- Dependencies only in `pyproject.toml` (+ `uv.lock` committed); no `requirements.txt` / `setup.py`.
- Git flow: `master` (production) + `develop` (integration); changes land via PR.
- Default: do not commit — git is the user's call.

## Commit Message Format

**NEVER add `Co-Authored-By: Claude ...` (or any other Claude/Anthropic attribution) to commit messages.**

This overrides the default Claude Code behavior of appending a `Co-Authored-By` trailer. Commit messages MUST contain only the user's authored content — no robot footer, no "Generated with Claude Code" line, no co-author trailer.

Same rule applies to PR descriptions: no `Generated with [Claude Code]` footer.
