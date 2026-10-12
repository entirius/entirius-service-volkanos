# entirius-service-volkanos

The backend service of Entirius, the open-source modular ecommerce platform: a thin Django shell that runs the
platform's modules behind one REST API. Every module is its own repository and package; the service adds
settings, URL routing, authentication and the OpenAPI schema.

[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://github.com/entirius/entirius-service-volkanos/blob/develop/pyproject.toml)
[![License: MPL-2.0](https://img.shields.io/badge/license-MPL--2.0-blue.svg)](https://github.com/entirius/entirius-service-volkanos/blob/develop/LICENSE)

## What it does

- Runs the Entirius modules (catalog, pricing, content, checkout, accounts and more) as one Django project.
- Lets every environment choose its modules: nothing is enabled until `main/settings_local.py` lists it.
- Serves the admin and storefront REST APIs with an OpenAPI schema, Swagger UI and ReDoc.
- Issues staff tokens and gates the admin API by role through the access module.
- Refuses to boot without an explicit per-environment configuration.

## Installation

```bash
git clone https://github.com/entirius/entirius-service-volkanos.git
cd entirius-service-volkanos
make install     # uv sync
```

## Quick start

`main/settings_local.py` is required: the service refuses to boot without it. It is per environment, gitignored,
and must define `ENVIRONMENT`, `SECRET_KEY` and `DATABASES`; the template is `main/settings_example.py`.

```bash
printf 'ENVIRONMENT=development\n' > .env   # the dev-only targets read it
make init                                   # settings_local.py from the example, migrate, test users
make run                                    # dev server on http://localhost:8000
```

`make init` creates the users of `scripts/test_users.example.yaml` (copy it to `scripts/test_users.yaml` to set
your own passwords). Sign in at http://localhost:8000/admin/ as `admin` (the password is in that file), then open
http://localhost:8000/api/schema/swagger-ui/ in the same browser: the schema and its UIs answer staff only.
`API_SCHEMA_PUBLIC = True` in `main/settings_local.py` serves them anonymously.

Without `make init`, do the same by hand: `uv sync`, copy `main/settings_example.py` to
`main/settings_local.py`, `uv run python manage.py migrate`, `uv run python manage.py runserver`.

## Choosing modules

[modules.yaml](https://github.com/entirius/entirius-service-volkanos/blob/develop/modules.yaml) lists every module
and library the service depends on: what each one does, what it requires, the worker queues it uses, the settings
it reads and whether it routes URLs.

- Enabling a module: its package in `pyproject.toml`, its app in `LOCAL_APPS` (`main/settings_local.py`) in
  registry order, together with the apps of its `requires` and `also_enable`, and a URL guard in `main/urls.py`
  when `urls: true`.
- The `platform` entry (access) is never listed: the service enables it itself in every environment.
- The worker consumes `celery` plus the `queues` of every enabled module: `celery -A main worker -Q <list>`.
- `make settings-example` regenerates the module list of `main/settings_example.py` from the registry.
- `make first-channel` creates the first sales channel on a migrated, empty database.

## Requirements

- Python 3.12 or newer, Django 5.2 or newer, [uv](https://docs.astral.sh/uv/).
- PostgreSQL through `DATABASE_URL`; without it a bare service falls back to SQLite (enough to boot and browse
  the schema, not for the modules that need PostgreSQL).
- The enabled modules bring their own needs (Redis, a Celery broker): see `modules.yaml`.

## Documentation

- Entirius documentation: https://docs.entirius.com/
- Module registry: https://github.com/entirius/entirius-service-volkanos/blob/develop/modules.yaml
- Changelog: https://github.com/entirius/entirius-service-volkanos/blob/develop/CHANGELOG.md

## Part of Entirius

The service is the backend of the platform; the frontends and the harness are separate repositories.

- Docker harness (the full stack, seeded): https://github.com/entirius/entirius-zeno
- Admin CMS: https://github.com/entirius/entirius-pwa-cms
- Storefront: https://github.com/entirius/entirius-pwa-storefront
- Test package (seed data, BDD, end-to-end): https://github.com/entirius/entirius-test-package-emporium
- Modules: https://github.com/entirius/entirius-django-pim (catalog),
  https://github.com/entirius/entirius-django-access (staff roles and API tokens)

## Development

```bash
make help        # list all targets
make check       # lint + format check (ruff)
make test        # migration drift check + tests (pytest)
```

The dev-only targets (`init`, `recreate-db`, `reinstall`, `rebuild`, `test-users`) refuse to run unless `.env`
says `ENVIRONMENT=development`. Development and agent instructions:
https://github.com/entirius/entirius-service-volkanos/blob/develop/AGENTS.md

## License

Mozilla Public License 2.0 (MPL-2.0) — see https://github.com/entirius/entirius-service-volkanos/blob/develop/LICENSE.
