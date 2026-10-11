# AGENTS.md

`entirius-service-volkanos` — the backend service of Entirius (Django project `main`): a thin Django + DRF shell
that runs the `entirius-py-*` / `entirius-django-*` modules, each released from its own repository.

## Commands

| Command | Meaning |
|---|---|
| `make install` | sync dependencies (uv) |
| `make check` / `make fix` | lint + format (ruff) |
| `make test` | migration drift check + pytest |
| `make run` / `migrate` / `makemigrations` / `shell` / `schema` | Django dev tasks |
| `make settings-example` | regenerate the module list of `main/settings_example.py` from `modules.yaml` |
| `make first-channel` | first channel on a migrated, empty database, in every enabled module, with a storefront key (`CONFIG=`, default `scripts/first-channel.example.toml`; idempotent; `createsuperuser` first) |
| `make health` | prod-safe read-only health check |
| `make init` / `settings-local` / `recreate-db` / `reinstall` / `rebuild` / `test-users` | dev-only, fail-closed on `ENVIRONMENT` |

Dev-only tasks require `ENVIRONMENT=development` in `.env` — they refuse to run otherwise.
`make init` = `settings-local` (copies `main/settings_example.py` to `main/settings_local.py` when absent) +
`migrate` + `test-users` (`scripts/test_users.yaml`, else `scripts/test_users.example.yaml`).
One-time: `uv run pre-commit install` (git hooks: ruff + MPL license header + gitleaks).

## Conventions

- English only: code, docs, commits, branches, PRs.
- MPL-2.0: every non-trivial source file carries the license header (pre-commit inserts it, CI enforces).
- Dependencies only in `pyproject.toml` (+ `uv.lock` committed); no `requirements.txt` / `setup.py`.
- Toolchain: uv (packages), ruff (lint + format), hatchling (build), pytest; OpenAPI by drf-spectacular.
- Git flow: `master` (production) + `develop` (integration); changes land via PR.
- Default: do not commit — git is the user's call.

### Commit Message Format

**NEVER add `Co-Authored-By: Claude ...` (or any other Claude/Anthropic attribution) to commit messages.**

This overrides the default Claude Code behavior of appending a `Co-Authored-By` trailer. Commit messages MUST contain only the user's authored content — no robot footer, no "Generated with Claude Code" line, no co-author trailer.

Same rule applies to PR descriptions: no `Generated with [Claude Code]` footer.

## Architecture

```
apps/platform/         # the service's own app: token views, failed-login guard wiring, deploy checks
main/                  # Django project: settings.py, settings_example.py, security.py, urls.py, wsgi, asgi
scripts/               # first_channel.py, ensure_test_users.py, render_settings_example.py
tests/                 # smoke, registry, hardening and access-route tests
modules.yaml           # registry of every module and library the service depends on
.github/workflows/     # CI (lint + test)
```

Modules **do not live in this repo** — each is its own repo, installed as a dependency.
Adopting an `entirius-django-*` module = dependency in `pyproject.toml` (+ `uv lock`),
its app in `LOCAL_APPS` (`main/settings_local.py`; empty by default), `include()` of its urls in `main/urls.py`.
Plain `entirius-py-*` libraries are dependencies only — no `LOCAL_APPS` / urls wiring.
Adopting a module does not change its name / app_label / DB tables.
The registry of modules and libraries is `modules.yaml`, kept true by `tests/test_modules_registry.py`.

Access is the one module the service installs itself: when `entirius-django-access` is importable, `main/settings.py`
adds `django_access` to `LOCAL_APPS`, the access gate middleware and the `ApiKeyAuth` OpenAPI hook, and
`main/urls.py` includes `django_access.urls` and serves `api/token/` and `admin/login/` through the failed-login
guard (`StaffTokenView`). No environment lists it.

Per-environment config: `main/settings_local.py` (gitignored) is REQUIRED — the service refuses to boot without it;
template `main/settings_example.py`; it must define `ENVIRONMENT`, `SECRET_KEY`, `DATABASES`.
DB: `DATABASE_URL` env var (PostgreSQL under entirius-zeno / CI); SQLite fallback.

| Topic | Where |
|---|---|
| Module registry: requirements, queues, settings, URL routing | `modules.yaml` |
| Settings template, generated module list | `main/settings_example.py` |
| First-channel config | `scripts/first-channel.example.toml` |
| Release history | `CHANGELOG.md` |

## Settings

Defaults live in `main/settings.py`; values that feed DRF / drf-spectacular are applied after the settings_local import.
DRF's default authentication is JWT only (`REST_FRAMEWORK` in `main/settings.py`): a view without its own classes never
reads Basic credentials or a session; `volkanos.E002` in `check --deploy` fails when either class is in the defaults.

| Setting | Default | Meaning |
|---|---|---|
| `DRF_NUM_PROXIES` | `None` | trusted `X-Forwarded-For` hops for per-IP throttles; `0` = no proxy, `1` behind Cloudflare → Caddy → nginx; unset → `volkanos.E001` in `check --deploy` (any `DEBUG`) |
| `API_SCHEMA_PUBLIC` | `False` | `True` serves `api/schema/`, swagger-ui and redoc anonymously; otherwise staff only |
| `ACCESS_GATE_MODE` | `enforce` | access gate on the admin API (read by `django_access`): `enforce` \| `observe` (log refusals, let through) \| `off`; no access, no gate |
| `AUTH_TOKEN_FAILURE_WINDOW_S` | `900` | window of the failed-login counters on `api/token/` and the admin login form `admin/login/` (read by `django_access.services.login_guard`; no access, no counter) |
| `AUTH_TOKEN_MAX_FAILURES_PER_USER_IP` | `10` | failures per username + address before 429 |
| `AUTH_TOKEN_MAX_FAILURES_PER_IP` | `100` | failures per address before 429 |
| `AUTH_TOKEN_MAX_FAILURES_PER_USER` | `50` | failures per username from any address before 429 |
| `AUTH_TOKEN_USER_FAILURE_WINDOW_S` | `3600` | window of the per-username counter (`Retry-After` when it blocks) |
