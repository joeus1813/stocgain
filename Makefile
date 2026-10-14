SHELL := /bin/sh
UV ?= uv
NPM ?= npm
PRESET ?= standard
SEED ?= 42
BACKEND = $(UV) run --project backend --locked

.PHONY: help setup db-up db-down db-reset migrate seed analytics pipeline api web dev demo-docker test test-backend test-frontend e2e lint typecheck openapi check-openapi explain schema-dump verify

help:
	@echo 'Setup: make setup; make db-up; make api and make web in separate terminals'
	@echo 'Verify: make lint typecheck test; make e2e requires running API, web and PostgreSQL'
	@echo 'Types: make openapi; make check-openapi'
	@echo 'Stage 1 incomplete: migrate, seed, analytics, pipeline, dev, demo-docker, explain, schema-dump, db-reset are not implemented.'
	@echo 'Future seed interface: make seed PRESET=standard SEED=42'

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
	$(BACKEND) uvicorn stocksense.api.app:app --reload --port 8000

web:
	cd frontend && $(NPM) run dev

lint:
	$(BACKEND) ruff check backend
	$(BACKEND) ruff format --check backend
	cd frontend && $(NPM) run lint

typecheck:
	cd backend && $(UV) run --locked mypy src/stocksense
	cd frontend && $(NPM) run typecheck

test: test-backend test-frontend

test-backend:
	$(BACKEND) pytest backend/tests

test-frontend:
	cd frontend && $(NPM) run test

e2e:
	cd frontend && $(NPM) run e2e

openapi:
	$(BACKEND) python -m stocksense.api.export_openapi frontend/openapi.json
	cd frontend && $(NPM) run gen:api

check-openapi:
	@tmp=$$(mktemp -d); trap 'rm -rf "$$tmp"' EXIT; \
	$(BACKEND) python -m stocksense.api.export_openapi "$$tmp/openapi.json" && \
	cd frontend && ./node_modules/.bin/openapi-typescript "$$tmp/openapi.json" -o "$$tmp/schema.ts" && \
	diff -u openapi.json "$$tmp/openapi.json" && diff -u src/lib/api/schema.ts "$$tmp/schema.ts"

verify:
	$(MAKE) lint
	$(MAKE) typecheck
	$(MAKE) test
	$(MAKE) check-openapi

db-reset migrate seed analytics pipeline dev demo-docker explain schema-dump:
	@echo 'Not implemented in the current Phase 0 checkpoint: $@. See IMPLEMENTATION_STATUS.md.' >&2
	@exit 2
