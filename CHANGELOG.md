# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Adopted Stage 1 leaf libraries from PyPI (>=2.0.0): `entirius-py-bievents`,
  `entirius-py-graylog-json-formatter`, `entirius-py-int-enum-choices`,
  `entirius-py-lockfile`, `entirius-py-idx-normalizator`.

## [3.0.0a1] - 2026-07-01

First public pre-release of the Volkanos service. Alpha — modules land stage by stage;
`3.0.0` final ships with all modules in.

### Added

- Base Django + DRF service skeleton (Stage 0): settings, URL routing,
  OpenAPI schema via drf-spectacular (schema / Swagger UI / ReDoc).
- Toolchain: uv (env + lock), ruff (lint + format), hatchling (build), pytest (+ pytest-django).
- Makefile task runner: prod-safe (`health`, `check`, `test`) and dev-only verbs
  (`init`, `reset-db`, `reinstall`, `rebuild`, `test-users`) guarded by `ENVIRONMENT`.
- CI (GitHub Actions): lint + test + secret-scan (gitleaks).
- MPL 2.0 license with per-file headers; pre-commit (ruff + license header + gitleaks).
