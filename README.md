# entirius-service-volkanos

Volkanos — base Django service of the Entirius platform. A thin shell (Django + DRF)
that bottom-up adopts `entirius-py-*` / `entirius-django-*` modules, each released
as its own repo and usable standalone.

## Stack

- Django 5.2+ with Django REST Framework
- drf-spectacular (OpenAPI 3.0)
- uv (packages), ruff (lint + format), hatchling (build), pytest
- DB: `DATABASE_URL` env var (postgres under entirius-zeno / CI); sqlite fallback for bare local dev

## Quick start

Per-environment config: copy `main/settings_example.py` -> `main/settings_local.py` (gitignored).
The file is REQUIRED - the service refuses to boot without it (fail-closed: no explicit
env type, DB and secret key means the environment was never consciously configured).

```bash
uv sync                      # install dependencies + dev
cp main/settings_example.py main/settings_local.py
uv run python manage.py migrate
uv run python manage.py runserver
```

- API schema:  http://localhost:8000/api/schema/
- Swagger UI:   http://localhost:8000/api/schema/swagger-ui/
- ReDoc:        http://localhost:8000/api/schema/redoc/
- Admin:        http://localhost:8000/admin/

## Choosing modules

[modules.yaml](modules.yaml) lists every module and library the service depends on: what each one does,
what it requires, the worker queues it uses, the settings it reads and whether it routes URLs.

- Enabling a module: its package in `pyproject.toml`, its app in `LOCAL_APPS` (`main/settings_local.py`) in
  registry order, together with the apps of its `requires` and `also_enable`, and a URL guard in `main/urls.py`
  when `urls: true`.
- The `platform` entry (access) is never listed: the service enables it itself wherever the package is installed.
- The worker consumes `celery` plus the `queues` of every enabled module: `celery -A main worker -Q <list>`.
- `make settings-example` regenerates the module list of `main/settings_example.py` from the registry.

## Development

```bash
make help        # list all tasks
make check       # lint + format check
make test        # migration drift check + tests
make run         # dev server
```

Dev-only tasks (`init`, `recreate-db`, `reinstall`, `rebuild`, `test-users`) require
`ENVIRONMENT=development` in `.env` — they refuse to run otherwise (fail-closed).

## Layout

```
apps/                  # Volkanos modules (LOCAL_APPS) — wired in as they are adopted
main/                  # Django project (settings, urls, wsgi, asgi)
tests/                 # base smoke tests
.github/workflows/     # CI (lint + test)
```

## Conventions

English-only (code, docs, git, API); MPL-2.0 with per-file headers; git-flow
(`master` + `develop`, PR-only). Development and agent instructions: [AGENTS.md](AGENTS.md).

## License

Mozilla Public License 2.0 — see [LICENSE](LICENSE).
