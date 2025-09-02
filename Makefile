SHELL := /bin/bash

# Environment variables expected:
# - DATABASE_URL: e.g., postgresql+psycopg2://mcg_user:PASS@localhost:5432/mcg_db
# - PERSONAL_PATH: path to conversations.json (default: db/chat data/conversations.json)
# - SOURCE: label for personal import (default: openai_chatgpt)
# - SOCIAL_PATH: path to social posts JSON (array)
# - PLATFORM: social platform label (default: twitter)
# - PUBLISHED_PATH: path to published articles JSON (array)
# - DEFAULT_AUTHORITY: default authority score for unknown domains (default: 0.0)
# - COMPOSE: docker compose command (default: docker compose -f src/docker-compose.yml)

PERSONAL_PATH ?= db/chat data/conversations.json
SOURCE ?= openai_chatgpt
SOCIAL_PATH ?=
PLATFORM ?= twitter
PUBLISHED_PATH ?=
DEFAULT_AUTHORITY ?= 0.0
COMPOSE ?= docker compose -f src/docker-compose.yml

.PHONY: help migrate import-personal ingest-social ingest-published tests compose-up compose-down compose-import-personal

help:
	@echo "Targets:"
	@echo "  migrate                 - Alembic upgrade head (requires DATABASE_URL)"
	@echo "  import-personal         - Import ChatGPT conversations.json (PERSONAL_PATH, SOURCE)"
	@echo "  ingest-social           - Import social posts (SOCIAL_PATH, PLATFORM)"
	@echo "  ingest-published        - Import articles (PUBLISHED_PATH, DEFAULT_AUTHORITY)"
	@echo "  tests                   - Run pytest"
	@echo "  compose-up              - Start Postgres/Redis/app via docker compose"
	@echo "  compose-down            - Stop compose services"
	@echo "  compose-import-personal - Import personal data inside app container (/data/conversations.json)"

migrate:
	@test -n "$$DATABASE_URL" || (echo "ERROR: DATABASE_URL is not set" >&2; exit 1)
	python -m mcg_agent.ingest.seed --upgrade-db

import-personal:
	@test -n "$$DATABASE_URL" || (echo "ERROR: DATABASE_URL is not set" >&2; exit 1)
	@test -f "$(PERSONAL_PATH)" || (echo "ERROR: PERSONAL_PATH not found: $(PERSONAL_PATH)" >&2; exit 1)
	python -m mcg_agent.ingest.seed --personal-path "$(PERSONAL_PATH)" --source "$(SOURCE)"

ingest-social:
	@test -n "$$DATABASE_URL" || (echo "ERROR: DATABASE_URL is not set" >&2; exit 1)
	@test -n "$(SOCIAL_PATH)" || (echo "ERROR: Set SOCIAL_PATH to your posts.json" >&2; exit 1)
	python -m mcg_agent.ingest.social_loader --path "$(SOCIAL_PATH)" --platform "$(PLATFORM)"

ingest-published:
	@test -n "$$DATABASE_URL" || (echo "ERROR: DATABASE_URL is not set" >&2; exit 1)
	@test -n "$(PUBLISHED_PATH)" || (echo "ERROR: Set PUBLISHED_PATH to your articles.json" >&2; exit 1)
	python -m mcg_agent.ingest.published_loader --path "$(PUBLISHED_PATH)" --default-authority "$(DEFAULT_AUTHORITY)"

tests:
	pytest tests/

compose-up:
	$(COMPOSE) up -d --build

compose-down:
	$(COMPOSE) down -v

compose-import-personal:
	$(COMPOSE) exec app bash -lc "python -m mcg_agent.ingest.seed --personal-path '/data/conversations.json' --source '$(SOURCE)'"

