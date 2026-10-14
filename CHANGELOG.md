# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- AI studio seeds in `fixtures/common/`: `profile_demo.json` (company profile of the fictitious Orbital Foundry,
  version 1), `enrichment_workers.json` gains the `pim.writer` / `pim.tagger` workers with the `meta`, `description`
  and `tags` templates (the old `field` workers are inactive), `article_workflow.json` (step workers, templates and
  the `article` workflow: questions → search phrases → outline → draft → metadata → ContentDB document). Every
  worker's model is blank (the toolbox channel's first allowed model). Load with
  `manage.py loaddata fixtures/common/enrichment_workers.json fixtures/common/article_workflow.json fixtures/common/profile_demo.json`;
  `tests/test_enrichment_seeds.py` validates them. The seeds need the `entirius-django-enrichment` release that
  ships contract A3/A4 (profile schema, templates, workflows); the lock still pins 2.2.0, so the tests skip and a
  baked stack cannot load them until the pin is bumped. `profile_demo.json` is for an empty demo database only: it
  writes the instance profile and its version-1 snapshot directly, past `profile_service`, so loading it over a
  profile saved through the API replaces that profile and breaks its version history.

## [4.0.1] - 2026-10-13

### Fixed

- `entirius-django-matrix` 4.4.1: products no longer go missing from the storefront API after a seed or a large
  import (two read-model fills of one channel could delete each other's rows). Rows lost on an earlier version come
  back with `python manage.py fill-read-model --channel_idx <channel>`.

## [4.0.0] - 2026-10-12

A major release: `entirius-django-access` is a required dependency, the default authentication is JWT only and the
module keys are access tokens. Read `### Changed` and `### Security` before upgrading.

### Added

- Access wiring: when `entirius-django-access` is importable, `django_access` joins `INSTALLED_APPS`, the
  `AccessGateMiddleware` is appended last to `MIDDLEWARE`, its URLs are mounted (`api/access/v2/`) and the OpenAPI
  document gains the `ApiKeyAuth` scheme on the token-scope routes. The gate runs in its default `enforce` mode;
  environments override `ACCESS_GATE_MODE` in `settings_local`.
- `tests/test_access_routes.py`: every admin route has an access area, the token-scope routes stay outside the admin
  set; `tests/test_access_security.py`: public set untouched (0 queries), admin principal sweep (a token is anonymous
  there), route-map invariants, path mutations, OpenAPI exposure, no `x-api-admin-key` in CORS.
- `DRF_NUM_PROXIES` (settings_local, default None = DRF's behaviour): copied into `REST_FRAMEWORK["NUM_PROXIES"]`
  after the settings_local import, so per-IP throttles trust only that many `X-Forwarded-For` hops. Deployment check
  `volkanos.E001` (Error, tag `entirius_config`, `check --deploy` only) fails whenever it is unset, in any `DEBUG`;
  `0` = no proxy, behind Cloudflare → Caddy → nginx the value is `1`. Every deployment must set it before upgrading.
  `settings_example.py` carries it commented out, so a copied template fails `check --deploy` until it is chosen.
- Service app `apps.platform` (label `volkanos_platform`, no models): the E001 check and the staff login view.
- `tests/test_platform_hardening.py`: proxies, E001, OpenAPI access per principal, the login throttle.

### Changed

- **Breaking:** `entirius-django-access` (1.0.0 or later) is a required dependency. `main/settings.py` enables
  `django_access` in every environment and refuses to start without the package. It was enabled only where the
  package happened to be installed.
- The module floors in `pyproject.toml` are the versions released with this one (the key modules as majors).
- The OpenAPI document and its swagger/redoc UIs are served to staff only (`IsAdminUser`, JWT or Django admin
  session; 401 anonymous, 403 customers) unless `API_SCHEMA_PUBLIC = True` in settings_local.
- OpenAPI: `POST api/token/` and `POST api/token/refresh/` carry the `Authentication` tag (they fell back to the
  default tag). The token views are thin tagged subclasses in `apps/platform/token_views.py`; routes, URL names and
  behaviour are unchanged.
- modules.yaml: no module forces another one any more (`also_enable` is empty for matrix, qms and accounts; the
  modules no longer crash when an optional sibling app is installed but not enabled).

### Security

- `api/token/` counts failed logins per username + address (`AUTH_TOKEN_MAX_FAILURES_PER_USER_IP`, 10) and per
  address (`AUTH_TOKEN_MAX_FAILURES_PER_IP`, 100) within `AUTH_TOKEN_FAILURE_WINDOW_S` (900 s); at the limit it
  answers 429 with `Retry-After`, also for a correct password. Successes are never counted and clear the username +
  address counter; cache keys hold hashes only. Behaviour change for anyone scripting `api/token/` with wrong
  passwords. The counter is access' public `django_access.services.login_guard` (same settings and key shape); without
  `django_access` installed `api/token/` is SimpleJWT's own view, unthrottled. The CMS customer login
  (`customer/tokens/`) is not covered yet (accounts adopts the guard).
- The guard's third counter, failed logins per username from any address (`AUTH_TOKEN_MAX_FAILURES_PER_USER`, 50
  within `AUTH_TOKEN_USER_FAILURE_WINDOW_S`, 3600 s; both declared in `main/settings.py`), applies to `api/token/` unchanged; `Retry-After` is now the
  window of the counter that blocks (the longest when several do), not always `AUTH_TOKEN_FAILURE_WINDOW_S`.
- `REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]` is set to JWT only. It was unset, so DRF's own defaults (session
  and Basic) applied to every view that declares no classes: a public route answered differently for a right and a
  wrong password sent as `Authorization: Basic`, outside the failed-login counters of `api/token/`. Such a view now
  ignores Basic credentials and session cookies. Deployment check `volkanos.E002` (Error, `check --deploy` only) fails
  when `BasicAuthentication` or `SessionAuthentication` is in the defaults; an environment that replaces
  `REST_FRAMEWORK` in settings_local must keep the key. Views that declare their own classes are unchanged, and so
  are the Django admin and the staff-only schema UIs (JWT or admin session, declared).
- The Django admin login form (`admin/login/`) counts on the failed-login counters of `api/token/`: the same limits
  per username + address, per address and per username, and a login blocked on one is blocked on the other (429 with
  `Retry-After`, also for a correct password). The form accepted unlimited guesses, also while `api/token/` was
  blocked. Wired only where `django_access` is installed; no new setting.
### Fixed

- `AUTHENTICATION_BACKENDS` registers `django_accounts.backends.JWTAccessBackend` (before `ModelBackend`) when
  `django_accounts` is installed. Without it the customer Bearer token was never read: `customer/me/`, profile,
  addresses, wishlist, password change, logout, and the checkout/returns/vault customer views answered 401.

## [3.0.1] - 2026-09-30

### Security

- `entirius-django-pim>=3.3.1` — the legacy `/api-viewer/pim/` routes (11, one of them an anonymous PUT that
  overwrote `Attribute.extension`) require a staff JWT.

## [3.0.0] - 2026-09-30

First final release of the 3.0 line: every platform module from PyPI, the leads platform, and the CMS 3.x backend.

### Changed

- `entirius-django-pim>=3.3.0` — required features per feature set (off by default,
  `PIM_ENFORCE_REQUIRED_ON_CREATE` / `PIM_STRICT_CREATE`), declared units of weight/dimensions; migration `django_pim.0063`.
  CMS 3.1.0 detects it and renders required fields on product create.
- `entirius-django-pim-csv>=4.1.0` — optional `required` column in the features-in-feature-sets CSV.
- `entirius-django-pricemanager>=4.2.1` — `manage-pricelists` exits cleanly with no price lists.

### Verified

- Full harness `LOCAL_APPS` (43 apps) on PostgreSQL 16 + pgvector: 515 migrations across 44 apps apply,
  `makemigrations --check` clean, `manage.py check` with only the dev-config warnings rc10 also had; pytest and ruff green.

## [3.0.0rc10] - 2026-09-30

### Security

- PyJWT 2.14.0 (advisories published 2026-09-30, one critical). oauthlib stays at 3.3.1: 4.0.0 would force django-allauth
  back from 65.18 to 65.9 (newer allauth caps oauthlib < 4) — the two medium oauthlib alerts stay open until allauth
  supports oauthlib 4.

## [3.0.0rc9] - 2026-09-30

Leads platform and the CMS 3.0 backend: every module from PyPI, security lock refresh.

### Added

- Leads platform modules from PyPI — `entirius-django-notifications[googlechat]`, `entirius-django-siteintel>=0.2.0`,
  `entirius-django-communicator>=0.3.0`, `entirius-django-leads>=0.3.0` (deps, LOCAL_APPS template entries, guarded URL
  includes); the CMS Leads panel (inbox, review, board, lead types, contacts) runs on them.
- `entirius-django-lookup`, `entirius-django-atlas`, `entirius-django-pricefighter` from PyPI with their routes mounted
  when installed; lookup runtime deps (pgvector, imagehash, rapidfuzz, python-stdnum).

### Changed

- Floors: `entirius-django-munin>=2.2.0` (configuration health `health/`), `entirius-django-email>=4.1.0` (per-channel
  SMTP status and checks), `entirius-django-pim>=3.2.2`, `entirius-django-lookup>=0.3.0`, `entirius-django-contentdb>=5.1.0`,
  utils 2.2.0, pim-csv 4.0.0; path sources removed — every module resolves from PyPI.
- OpenAPI 3.1 schema (Pydantic examples validate); the API version is read from `pyproject.toml`.

### Security

- Lock refresh closing the open Dependabot alerts: anyio 4.14.2, cryptography 50.0.1, Django 6.0.8, Django REST
  framework 3.17.2, sqlparse 0.6.0, soupsieve 2.10. PyPDF2 has no fixed release (abandoned upstream) and stays open.

## [3.0.0rc7] - 2026-07-31

Supplementary Core migrations — contact forms and REGON lookup join the platform.

### Added

- `entirius-django-contact-forms[bookings,google-ads]>=3.0.0` (dep, LOCAL_APPS template entry,
  URL wiring) — contact forms, bookings, leads, ad-conversion uploads; unlocks the CMS
  ContactForms section.
- `entirius-django-regon-api>=3.0.0` (dep, LOCAL_APPS template entry, URL wiring) —
  NIP/REGON lookup against Polish government registries; no models.

## [3.0.0rc6] - 2026-07-31

Module cleanup wave 2 — django-crm withdrawn from the public platform.

### Removed

- `entirius-django-crm` (dep, LOCAL_APPS template entry, URL wiring).

### Changed

- Floor: `entirius-django-getresponse>=3.0.0` — contact carries its own email,
  marketing consent gate reads `django-agreements`.

## [3.0.0rc5] - 2026-07-30

Module cleanup — five modules withdrawn from the public platform.

### Removed

- `entirius-django-pim-export-to-magento-package`, `entirius-django-vat-validator`,
  `entirius-django-pricetuner`, `entirius-django-loyalty`, `entirius-django-checkout-voucher`
  (deps, LOCAL_APPS template entries, URL wiring, voucher signal flag and secrets docs).

### Changed

- Floors: `entirius-django-checkout[qms,vault,returns]>=9.2.0`, `entirius-django-matrix[qms,pricemanager]>=4.2.0`
  (releases without the withdrawn extras).
- Stewardship metadata: maintainers in pyproject, CODEOWNERS, Commit Message Format block in AGENTS.md.

## [3.0.0rc1] - 2026-07-13

Stabilization — dependency floors raised to the patched module releases.

### Changed

- `entirius-django-baselinker>=2.0.1` (fixes NameError on API error paths in the client),
  `entirius-django-accounts>=5.0.1` (fixes broken password-validator help text),
  `entirius-django-omnibus>=3.0.1` (fixes NameError on the pricemanager import fallback),
  `entirius-django-crm>=3.0.1` (newsletter consent and campaign resolution per channel).

## [3.0.0b1] - 2026-07-13

First beta — the full active module dependency graph is adopted from PyPI and verified
(fresh-database migrate plus existing-database upgrade, smoke and HTTP probes).

### Changed

- Development Status classifier: Alpha → Beta. No functional changes since 3.0.0a11.

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
