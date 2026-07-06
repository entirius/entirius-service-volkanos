.PHONY: help health install check fix test run migrate makemigrations \
        shell schema guard-dev reinstall recreate-db test-users init rebuild
.DEFAULT_GOAL := help

-include .env
export
# fail-closed: no declaration => prod => dev-only refused
ENVIRONMENT ?= production

help:  ## List targets
	@grep -E '^[a-z-]+:.*##' $(firstword $(MAKEFILE_LIST)) | awk -F':.*##' '{printf "  %-16s %s\n", $$1, $$2}'

# --- prod-safe (read-only; runnable anywhere incl. production) ---
health:  ## Prod-safe system health check (read-only)
	uv run python manage.py check
	uv run python manage.py check --database default
	uv run python manage.py migrate --check

# --- dev / CI (code correctness) ---
install:  ## Sync dependencies (uv)
	uv sync

check:  ## Lint + format-check (ruff) + canonical .gitleaks.toml
	@grep -q "forbidden-names" .gitleaks.toml 2>/dev/null || { echo "Missing or non-canonical .gitleaks.toml - symlink the config per the internal secret-scanning standard"; exit 1; }
	uv run ruff check .
	uv run ruff format --check .

fix:  ## Auto-fix lint + format
	uv run ruff check --fix .
	uv run ruff format .

test:  ## Migration drift check + test suite (pytest)
	uv run python manage.py makemigrations --check --dry-run
	uv run pytest -x -q

# --- service ops ---
run:  ## Dev server
	uv run python manage.py runserver
migrate:  ## Apply migrations
	uv run python manage.py migrate
makemigrations:  ## Create migrations
	uv run python manage.py makemigrations
shell:  ## Django shell
	uv run python manage.py shell
schema:  ## Generate OpenAPI schema
	uv run python manage.py spectacular --file schema.yaml

# --- dev-only, state-changing (guarded, fail-closed on ENVIRONMENT) ---
guard-dev:
	@case "$(ENVIRONMENT)" in \
	  development|local) : ;; \
	  *) echo "REFUSED: dev-only target on ENVIRONMENT=$(ENVIRONMENT). Set ENVIRONMENT=development in .env to allow."; exit 1 ;; \
	esac

reinstall: guard-dev  ## DEV-ONLY: rebuild venv from lock
	uv sync --reinstall

recreate-db: guard-dev  ## DEV-ONLY DESTRUCTIVE: wipe dev DB (db.sqlite3)
	@echo "Wiping dev DB (db.sqlite3)…"
	rm -f db.sqlite3

test-users: guard-dev  ## DEV-ONLY: create configured test users (scripts/test_users.yaml)
	uv run python scripts/ensure_test_users.py
init: guard-dev migrate test-users  ## DEV-ONLY: migrate + create test users
	@echo "Init complete."

rebuild: guard-dev reinstall recreate-db init check test  ## DEV-ONLY: full from-scratch local test (no integration)
	@echo "Rebuild complete."
