# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [3.0.0a11] - 2026-07-13

Stage 5 — checkout satellites adopted from PyPI (closes the module middle layer).

### Added

- Adopted from PyPI: `entirius-django-checkout-voucher>=2.0.0`,
  `entirius-django-checkout-export-to-magento-api>=2.0.0`,
  `entirius-django-checkout-import-from-magento-api>=2.0.0`, `entirius-django-getresponse>=2.1.0`,
  `entirius-django-returns>=3.0.0`, `entirius-django-omnibus>=3.0.0`, `entirius-django-crm>=3.0.0`,
  `entirius-django-loyalty>=2.0.0`.
- Conditional URL wiring (LOCAL_APPS-gated) for `django_checkout_voucher`, `django_returns`,
  `django_crm` and `django_loyalty` (the export/import satellites, `django_omnibus` and
  `django_getresponse` are command/task/receiver-only — no routes).
- Base settings: `MAGENTO2_URL_FOR_CHECKOUT_EXPORT` / `MAGENTO2_TOKEN_FOR_CHECKOUT_EXPORT`
  (read at import by `django_checkout_export_to_magento_api` tasks; real values per environment)
  and `USE_VALIDATE_VOUCHERS_SIGNAL = True` (routes checkout voucher validation through
  `django_checkout_voucher` signal handlers).
- Per-environment voucher-flow secrets documented in `settings_example.py`:
  `VOUCHER_LOOKUP_HMAC_KEY`, `CRYPT_SALT`.

### Changed

- `entirius-django-checkout` bumped to `>=9.1.0`, extras extended to
  `[qms,vault,vat,pricetuner,returns,voucher]`.

## [3.0.0a10] - 2026-07-12

Stage 5 — checkout core adopted from PyPI.

### Added

- Adopted from PyPI: `entirius-django-checkout[qms,vault,vat,pricetuner]>=9.0.0`.
- Conditional URL wiring (LOCAL_APPS-gated) for `django_checkout` (v1 + v2 API, payment webhooks).

### Changed

- `entirius-django-pricemanager` bumped to `>=4.0.1` (restores the `validate_access_to_price_list`
  re-export in `output.py` that `django_checkout` imports at startup).

## [3.0.0a9] - 2026-07-11

Stage 4 middle layer, wave 4 — adopted from PyPI.

### Added

- Adopted from PyPI: `entirius-django-reviews[magento]>=2.0.0`,
  `entirius-django-matrix[qms,pricemanager,pricetuner]>=4.0.0`.
- Conditional URL wiring (LOCAL_APPS-gated) for `django_reviews` and `django_matrix`.
- `django.contrib.postgres` in base `INSTALLED_APPS` (GinIndex / full-text search in `django_matrix`).

## [3.0.0a8] - 2026-07-11

Stage 4 middle layer, wave 3 — adopted from PyPI.

### Added

- Adopted from PyPI: `entirius-django-accounts-export-to-magento-api>=2.0.0`,
  `entirius-django-pricetuner>=2.0.0`, `entirius-django-vault>=2.0.0`.
- Conditional URL wiring (LOCAL_APPS-gated) for `django_vault` (`django_accounts_export_to_magento_api`
  and `django_pricetuner` are admin/command-only — no routes).

## [3.0.0a7] - 2026-07-11

Stage 4 middle layer, wave 2 — adopted from PyPI.

### Added

- Adopted from PyPI: `entirius-django-accounts[pim]>=5.0.0`, `entirius-django-suppliers[qms]>=2.0.0`,
  `entirius-django-contentdb-translator>=2.0.1`, `entirius-django-sitemap[pim,contentdb,faq]>=4.0.0`.
- Conditional URL wiring (LOCAL_APPS-gated) for `django_accounts`, `django_suppliers` and
  `django_contentdb_translator` (`django_sitemap` is worker-only — no routes).
- Base settings required by `django_accounts`: `PRIVATE_DIR`, `MIGRATION_0023_MECHANISM`,
  `JWT_SECRET` (defaults to `SECRET_KEY`, override per environment).

## [3.0.0a6] - 2026-07-11

Stage 4 middle layer, wave 1 — adopted from PyPI.

### Added

- Adopted from PyPI: `entirius-django-baselinker>=2.0.0`, `entirius-django-crypt>=2.0.0`,
  `entirius-django-enrichment>=2.0.0`, `entirius-django-contentdb>=5.0.0`.
- Conditional URL wiring (LOCAL_APPS-gated) for `django_enrichment` and `django_contentdb`
  (`django_baselinker` ships empty urlpatterns, `django_crypt` has no routes).

## [3.0.0a5] - 2026-07-10

Stage 4 leaves — remaining Django leaf modules adopted from PyPI.

### Added

- Adopted from PyPI: `entirius-django-vat-validator>=2.0.0`, `entirius-django-faq>=2.0.0`,
  `entirius-django-munin>=2.0.0`, `entirius-django-captcha>=2.0.0`, `entirius-django-agreements>=2.0.0`,
  `entirius-django-deliverypoints>=2.0.0`, `entirius-django-qms>=4.0.0`, `entirius-django-email>=4.0.0`.
- Conditional URL wiring (LOCAL_APPS-gated) for `django_vat_validator`, `django_faq`, `django_munin`,
  `django_agreements`, `django_deliverypoints`, `django_qms`, `django_email`
  (`django_captcha` exposes a decorator only — no routes).

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
