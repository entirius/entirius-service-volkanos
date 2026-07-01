# entirius-service-volkanos

Volkanos — base Django service of the Entirius platform. A thin shell (Django + DRF)
that bottom-up adopts `entirius-py-*` / `entirius-django-*` modules, each released
as its own repo and usable standalone.

Status: **Stage 0** — clean skeleton, no business modules yet.

## Stack

- Django 5.2+ with Django REST Framework
- drf-spectacular (OpenAPI 3.0)
- uv (packages), ruff (lint + format), hatchling (build), pytest
- DB: sqlite (Stage 0); PostgreSQL is added in Stage 2

## Quick start

```bash
uv sync                      # install dependencies + dev
uv run python manage.py migrate
uv run python manage.py runserver
```

- API schema:  http://localhost:8000/api/schema/
- Swagger UI:   http://localhost:8000/api/schema/swagger-ui/
- ReDoc:        http://localhost:8000/api/schema/redoc/
- Admin:        http://localhost:8000/admin/

Local settings: copy `main/settings_example.py` -> `main/settings_local.py`
and run with `DJANGO_SETTINGS_MODULE=main.settings_local`.

## Development

```bash
make help        # list all tasks
make check       # lint + format check
make test        # migration drift check + tests
make run         # dev server
```

Dev-only tasks (`init`, `reset-db`, `reinstall`, `rebuild`, `test-users`) require
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
