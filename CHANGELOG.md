# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [3.0.0a4] - 2026-07-10

Stage 3 complete — django-pim satellites and their dependencies adopted from PyPI.

### Added

- Adopted from PyPI: `entirius-django-pricemanager>=4.0.0`, `entirius-django-utils-translator>=2.0.0`,
  `entirius-django-pim-csv>=3.0.0`, `entirius-django-pim-translator>=2.0.0`,
  `entirius-django-pim-export-to-magento-api>=2.0.0`, `entirius-django-pim-export-to-magento-package>=2.0.0`.
- Conditional URL wiring for `django_pricemanager` and `django_pim_translator` (LOCAL_APPS-gated).
- Base settings required by the new modules: `DATA_DIR`, `EXPORT_DIR`, `BI_ENVIRONMENT`,
  `BI_BUSINESS_UNIT`, `T9N_DEFAULT_LANG`.

### Changed

- `entirius-django-regional` floor raised to `>=2.0.1` (postgres pk-sequence fix after seeded data).

## [3.0.0a3] - 2026-07-09

Stage 2/3 core — Django modules adopted from PyPI.

### Added

- Adopted from PyPI: `entirius-django-regional>=2.0.0`, `entirius-django-utils>=2.0.0`,
  `entirius-django-pim>=3.0.0`; per-environment `LOCAL_APPS` (settings_local) with conditional
  `django_pim.urls` include; `MEDIA_*`/`TMP_DIR` in base settings.

## [3.0.0a2] - 2026-07-06

Stage 1 complete — all Python leaf modules (libraries and SDKs) adopted from PyPI.

### Added

- Adopted Stage 1 leaf libraries from PyPI (>=2.0.0): `entirius-py-bievents`,
  `entirius-py-graylog-json-formatter`, `entirius-py-int-enum-choices`,
  `entirius-py-lockfile`, `entirius-py-idx-normalizator`, `entirius-py-process-logger`,
  `entirius-py-image-transformations`, `entirius-py-pdf-generator`.
- Adopted Stage 1 payment SDKs from PyPI (>=2.0.0): `entirius-py-payu-sdk`, `entirius-py-paypal-sdk`,
  `entirius-py-autopay-sdk`, `entirius-py-przelewy24-sdk`, `entirius-py-paynow-sdk`.
- Adopted Stage 1 integration SDKs from PyPI (>=2.0.0): `entirius-py-magento2-sdk`,
  `entirius-py-magento2-sdk2`, `entirius-py-synerise-sdk`, `entirius-py-salesmanago-sdk`,
  `entirius-py-edrone-sdk`; `entirius-py-get-response-sdk` (>=3.0.0).

### Changed

- Hardened gitleaks guard: canonical forbidden-names blocklist required (pre-commit + `make check`).

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
