SHELL := /bin/sh
UV ?= uv
NPM ?= npm
PRESET ?= standard
SEED ?= 42
LOAD_FLAGS ?=
BACKEND = $(UV) run --project backend --locked

.PHONY: help setup db-up db-down db-reset migrate seed analytics pipeline api web dev demo-docker test test-backend test-frontend e2e lint typecheck openapi check-openapi explain schema-dump verify

help:
	@echo 'Setup: make setup; make db-up; make api and make web in separate terminals'
	@echo 'Verify: make lint typecheck test; make e2e requires running API, web and PostgreSQL'
	@echo 'Types: make openapi; make check-openapi'
	@echo 'Phase 1: make migrate; make seed PRESET=standard SEED=42; stocgain data validate/profile'
	@echo 'Loading preserves existing data unless LOAD_FLAGS=--replace is explicitly supplied.'
	@echo 'Phase 2: stocgain db run-analysis 06; make explain benchmarks existing standard data'
	@echo 'Later-phase commands and db-reset remain unimplemented.'
	@echo 'Schema: make schema-dump writes sql/schema/current.sql from the running PostgreSQL container.'

setup:
	@node -e 'if (process.versions.node.split(".")[0] !== "22") { console.error("Node 22 is required; run nvm use"); process.exit(1); }'
	@test -f .env || cp .env.example .env
	$(UV) sync --project backend --locked
	cd frontend && $(NPM) ci

db-up:
	docker compose up -d --wait db

db-down:
	docker compose down

api:
	$(BACKEND) uvicorn stocgain.api.app:app --reload --port 8000

web:
	cd frontend && $(NPM) run dev

lint:
	$(BACKEND) ruff check backend
	$(BACKEND) ruff format --check backend
	cd frontend && $(NPM) run lint

typecheck:
	cd backend && $(UV) run --locked mypy src/stocgain
	cd frontend && $(NPM) run typecheck

test: test-backend test-frontend

test-backend:
	$(BACKEND) pytest backend/tests

test-frontend:
	cd frontend && $(NPM) run test

e2e:
	cd frontend && $(NPM) run e2e

openapi:
	$(BACKEND) python -m stocgain.api.export_openapi frontend/openapi.json
	cd frontend && $(NPM) run gen:api

check-openapi:
	@tmp=$$(mktemp -d); trap 'rm -rf "$$tmp"' EXIT; \
	$(BACKEND) python -m stocgain.api.export_openapi "$$tmp/openapi.json" && \
	cd frontend && ./node_modules/.bin/openapi-typescript "$$tmp/openapi.json" -o "$$tmp/schema.ts" && \
	diff -u openapi.json "$$tmp/openapi.json" && diff -u src/lib/api/schema.ts "$$tmp/schema.ts"

verify:
	$(MAKE) lint
	$(MAKE) typecheck
	$(MAKE) test
	$(MAKE) check-openapi

schema-dump:
	docker compose exec -T db pg_dump --schema-only --no-owner --no-privileges --restrict-key=stocgainSchemaDump42 -U stocksense stocksense > sql/schema/current.sql

migrate:
	$(BACKEND) alembic -c backend/alembic.ini upgrade head
	$(BACKEND) stocgain db apply-views

seed:
	$(BACKEND) stocgain data generate --preset $(PRESET) --seed $(SEED)
	$(BACKEND) stocgain data load --path data/generated/$(PRESET) $(LOAD_FLAGS)
	$(BACKEND) stocgain db apply-views
	$(BACKEND) stocgain data validate
	$(BACKEND) stocgain db refresh

explain:
	$(BACKEND) python backend/scripts/bench_sql.py

db-reset analytics pipeline dev demo-docker:
	@echo 'Not implemented in the current Phase 2 checkpoint: $@. See IMPLEMENTATION_STATUS.md.' >&2
	@exit 2
