# Multi-Corpus Governance Agent — Setup and Command Map

This guide gets you from zero to a working, populated database and shows every command and integration point implemented so far. It also summarizes the code layout so you can navigate quickly.

## Prerequisites
- Python 3.11+
- Postgres 16+ (recommended) or SQLite for local dev
- Optional: Docker + Docker Compose
- Optional: Redis (for caching and API call tracking)

## Environment Variables
- Core
  - `DATABASE_URL` (e.g., `postgresql+psycopg2://mcg_user:PASS@localhost:5432/mcg_db` or `sqlite:///./db.sqlite3`)
- Redis (optional)
  - `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`, `REDIS_TLS` (`true|false`)
  - `MCG_CACHE_BACKEND` (`redis|none`), `MCG_CACHE_TTL` (seconds)
  - `MCG_CALL_TRACKER_BACKEND` (`redis|memory`)
- MVLM (optional)
  - `MCG_MVLM_MODE` (`punctuation_only|noop|http`)
  - `MCG_MVLM_HTTP_URL`, `MCG_MVLM_HTTP_API_KEY`

## Local Setup (Python)
```
python -m venv .venv
source .venv/bin/activate
pip install -r src/requirements.txt
export DATABASE_URL="sqlite:///./db.sqlite3"   # or your Postgres DSN
```

## Database Migration (Alembic)
- Postgres: creates FTS generated columns + GIN indexes
- SQLite: tables are created by ORM; FTS migration is a no‑op
```
python -m mcg_agent.ingest.seed --upgrade-db
```

## Ingestion Commands
- Personal (ChatGPT export at `db/chat data/conversations.json`)
```
python -m mcg_agent.ingest.seed \
  --personal-path "db/chat data/conversations.json" \
  --source openai_chatgpt
```
- Social (JSON array of posts; see docs/ops/ingest-social.md)
```
python -m mcg_agent.ingest.social_loader --path path/to/posts.json --platform twitter
```
- Published (JSON array of articles; see docs/ops/ingest-published.md)
```
python -m mcg_agent.ingest.published_loader --path path/to/articles.json --default-authority 0.3
```

## Docker Compose (Dev)
- Compose file: `src/docker-compose.yml`
- Services: `postgres`, `redis` (dev), `app` (runs Alembic then idles)
```
# from repo root
export POSTGRES_PASSWORD=yourpass
export REDIS_PASSWORD=yourredispass   # only if enabling redis in app

docker compose -f src/docker-compose.yml up -d --build
# import personal data inside container
docker compose -f src/docker-compose.yml exec app \
  bash -lc "python -m mcg_agent.ingest.seed --personal-path '/data/conversations.json' --source openai_chatgpt"
```

## Caching and Call Tracking (optional)
```
export MCG_CACHE_BACKEND=redis
export MCG_CALL_TRACKER_BACKEND=redis
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_PASSWORD=yourredispass
```
- Connectors automatically cache search results (TTL default 90s)
- API call limits tracked per agent+task; Redis backend recommended in prod

## PydanticAI Tool Interfaces (used by agents)
Tools are registered in `src/mcg_agent/search/tools.py` and enforce governance via `SecureAgentTool`.
- `personal_search(query: str, filters: PersonalSearchFilters, limit: int = 20) -> PersonalSearchResult`
- `social_search(query: str, filters: SocialSearchFilters, limit: int = 30) -> SocialSearchResult`
- `published_search(query: str, filters: PublishedSearchFilters, limit: int = 20) -> PublishedSearchResult`

Filter and result models are defined in `src/mcg_agent/search/models.py`.

## Pipeline and Governance
- Routing pipeline: `src/mcg_agent/routing/pipeline.py`
  - Sequence: Ideator → Drafter → Critic → Revisor → Summarizer
  - Context assembly uses the PydanticAI tools under the Ideator role
  - Revisor/Summarizer integrate the MVLM provider (`src/mcg_agent/mvlm/provider.py`)
- Protocols (single source of truth): `src/mcg_agent/protocols/`
  - Governance: API limits, corpus/RAG access
  - Routing: pipeline order, revise template
  - Context: snippet + pack schemas
  - Punctuation: normalization policy
- Security stubs: `src/mcg_agent/security/` (Zero Trust headers, WAF stub, audit trail)

## Code Map
- DB
  - Models: `src/mcg_agent/db/models_{personal,social,published}.py`
  - Session: `src/mcg_agent/db/session.py`
  - Alembic: `alembic/*` (FTS and indexes for Postgres)
- Ingestion
  - Personal: `src/mcg_agent/ingest/personal_chatgpt_export.py` and wrapper `src/mcg_agent/ingest/seed.py`
  - Social: `src/mcg_agent/ingest/social_loader.py`
  - Published: `src/mcg_agent/ingest/published_loader.py`
- Search
  - Connectors: `src/mcg_agent/search/connectors.py` (Postgres FTS ranking with caching)
  - Tools (PydanticAI): `src/mcg_agent/search/tools.py`
- Governance & Security
  - API limits, call tracker, violations: `src/mcg_agent/governance/*`, `src/mcg_agent/utils/*`
  - Protocols: `src/mcg_agent/protocols/*`
- MVLM
  - Provider: `src/mcg_agent/mvlm/provider.py` (modes: `punctuation_only|noop|http`)

## Tests
```
pytest tests/
```
- Governance and routing checks are covered in `tests/` (protocols, API limits, pipeline, punctuation)

## Next Steps (TODO)
- Implement PydanticAI agents (Ideator/Drafter/Critic/Revisor/Summarizer) with secure tools and revise-call flow
- MVLM http mode integration with governance headers/timeouts
- Read replicas + PgBouncer (see `docs/ops/pgbouncer.ini.example` and `docs/ops/postgres.conf.example`)
- End‑to‑end tests with seeded fixtures

## Data Locations & Git Ignore
- Place exports and local databases under `db/` (e.g., `db/chat data/`, `db/social data/`, `db/published data/`).
  - The repository ignores `db/**` by default; `db/.gitkeep` keeps the folder only.
- Do not store datasets under `src/mcg_agent/db/` — that package is for Python code (ORM models, sessions). Accidental data patterns there are ignored (e.g., `*.sqlite3`, `*.json`, `data/`, `exports/`).
- Virtual environments are ignored globally (e.g., `**/venv/`, `**/.venv/`).
- Secrets belong in environment variables. `.env` is ignored.
- Quick verification before push:
  - `git status -s`
  - `git check-ignore -v "db/chat data/conversations.json"`
