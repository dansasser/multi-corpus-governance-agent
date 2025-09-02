# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment Setup
```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r src/requirements.txt
```

### Database Operations
```bash
# Database migration (requires DATABASE_URL)
make migrate
# or directly: python -m mcg_agent.ingest.seed --upgrade-db

# Import personal data (ChatGPT conversations.json)
make import-personal PERSONAL_PATH="db/chat data/conversations.json" SOURCE=openai_chatgpt

# Import social posts
make ingest-social SOCIAL_PATH=path/to/posts.json PLATFORM=twitter

# Import published articles
make ingest-published PUBLISHED_PATH=path/to/articles.json DEFAULT_AUTHORITY=0.3
```

### Testing and Code Quality
```bash
# Run tests
make tests
# or directly: pytest tests/

# Type checking and linting (optional but recommended)
mypy src/
ruff check src/
ruff format src/
```

### Docker Development
```bash
# Start services (Postgres, Redis, app)
make compose-up
# or: docker compose -f src/docker-compose.yml up -d --build

# Import data in container
make compose-import-personal SOURCE=openai_chatgpt

# Stop services
make compose-down
```

## Architecture Overview

### Five-Agent Governance Pipeline
This system implements a **governed AI pipeline** with strict guardrails and clear responsibilities:

#### Agent Flow & Responsibilities
1. **Ideator** (Entry Point)
   - Receives user prompt + multi-corpus context pack
   - Generates structured outline with tone/coverage scoring
   - **API Access**: Max 2 calls (1 initial + 1 revise if needed)
   - **Failure Handling**: Minor fail → local tweak, Major fail → single revise call, Critical fail → STOP
   
2. **Drafter** (Content Expansion)
   - Expands Ideator's outline into full draft
   - Applies voice samples from corpora for tone anchoring
   - **API Access**: Max 1 call per handoff
   - **SEO Integration**: Keywords, readability, headers (writing mode only)
   
3. **Critic** (Validation Authority)
   - **ONLY agent with full RAG access** for fact-checking
   - Voice check against corpus fingerprints
   - Truth/accuracy validation with external sources
   - **API Access**: Max 2 calls for validation and recheck
   
4. **Revisor** (MVLM Firebreak #1)
   - Applies Critic's corrections deterministically
   - **Primary Tool**: MVLM (Minimum Viable Language Model)
   - **Fallback**: 1 API call only if MVLM fails
   - May only add connector tokens (and, the, commas)
   
5. **Summarizer** (MVLM Firebreak #2)
   - Final packaging and long-tail keyword extraction
   - **Primary Tool**: MVLM only
   - **Fallback**: API only if governance explicitly allows
   - Zero new claims or vocabulary expansion

### Multi-Corpus Context Assembly
The system processes three distinct data sources through sophisticated context packing:

#### Corpus Types & Access Rules
- **Personal Corpus**: Chat history, notes, drafts (DB-only access)
  - **Allowed Agents**: Ideator, Critic
- **Social Corpus**: Posts, hashtags, engagement data (DB + RAG hybrid)
  - **Allowed Agents**: Ideator, Drafter, Critic
- **Published Corpus**: Articles, blogs, research (DB + RAG hybrid)  
  - **Allowed Agents**: Ideator, Drafter, Critic

#### Voice Fingerprinting System
- Per-corpus dictionaries of collocations and cadence markers
- Tone scoring based on fingerprint overlap
- Separate profiles for Personal (conversational), Social (colloquial), Published (formal)

#### Context Pack Structure
Each context pack includes:
- Attributed snippets with source, timestamp, tags
- Voice terms for tone alignment
- Usage notes explaining selection
- Coverage and diversity scoring

### Governance Enforcement Architecture

#### Routing Matrix Decision Logic
- **Minor Fail**: Single threshold miss → local tweak using corpus phrases
- **Major Fail**: Multiple threshold misses → exactly 1 revise API call with delta prompt
- **Critical Fail**: Safety/truth violations → pipeline STOP, requires human review

#### Strict API Call Limits
- **Total System Limit**: Max 7 API calls per user prompt (2+1+2+1+0)
- **Loop Prevention**: No agent may retry beyond their limit
- **MVLM Firebreaks**: Revisor + Summarizer default to local models

#### Attribution & Metadata Flow
- **Attribution**: Source + timestamp must persist through entire pipeline
- **Change Logs**: Track what Critic/Revisor modified and why
- **Long-tail Keywords**: Extracted by Summarizer, logged even if hidden
- **Metadata Bundle**: Complete provenance and decision audit trail

## Key Code Locations

### Core Application Structure
- `src/mcg_agent/main.py` - FastAPI application entry point
- `src/mcg_agent/config.py` - Environment-based configuration using Pydantic Settings
- `src/mcg_agent/agents/` - Agent implementations (Ideator, Drafter, etc.)

### Data Layer
- `src/mcg_agent/db/models_*.py` - SQLAlchemy models for each corpus
- `src/mcg_agent/db/session.py` - Database session management
- `alembic/` - Database migrations with PostgreSQL FTS and indexing

### Search and Tools
- `src/mcg_agent/search/connectors.py` - PostgreSQL FTS ranking with caching
- `src/mcg_agent/search/tools.py` - PydanticAI tool interfaces with governance
- `src/mcg_agent/search/models.py` - Search filter and result models

### Governance and Security
- `src/mcg_agent/protocols/` - Single source of truth for all governance rules
- `src/mcg_agent/governance/` - API limits, call tracking, violation handling
- `src/mcg_agent/security/` - Zero Trust headers, WAF stubs, audit trails

### Pipeline and Routing
- `src/mcg_agent/routing/pipeline.py` - Main agent pipeline orchestration
- `src/mcg_agent/mvlm/provider.py` - MVLM integration with multiple modes

## Important Environment Variables

### Database
- `DATABASE_URL` - PostgreSQL DSN or SQLite path (required)

### Redis (optional)
- `MCG_CACHE_BACKEND=redis` - Enable Redis caching
- `MCG_CALL_TRACKER_BACKEND=redis` - Redis-based API call tracking
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`, `REDIS_TLS`

### MVLM Configuration
- `MCG_MVLM_MODE` - `punctuation_only|noop|http`
- `MCG_MVLM_HTTP_URL`, `MCG_MVLM_HTTP_API_KEY` - For HTTP mode

## Classification & Routing System

### Prompt Classification Types
Every incoming prompt is classified to determine downstream processing:
- **Chat**: Conversational answers with Personal + Social corpus weighting
- **Writing**: Content drafting with SEO anchoring and Published corpus authority
- **Voice/Answering**: Real-time/telephony use cases with tone preservation
- **Retrieval-only**: Pure factual lookup with minimal processing

### Context Assembly Process
1. **Multi-corpus retrieval** based on classification
2. **Voice fingerprinting** with collocation scoring
3. **Context pack creation** with attribution preservation
4. **Threshold scoring**: Coverage (≥T1), Tone (≥T2), Diversity check

### Routing Decision Matrix
```
User Prompt → Classification → Multi-Corpus Retrieval → Context Assembly
     ↓
Ideator (outline + scoring) → Drafter (expansion + SEO) → Critic (validation + RAG)
     ↓                              ↓                        ↓
Minor fail: local tweak     Max 1 API call           Max 2 API calls + RAG
Major fail: 1 revise call   Pass to Critic           Annotate issues
Critical fail: STOP         
     ↓
Revisor (MVLM corrections) → Summarizer (MVLM packaging)
     ↓                           ↓
Apply Critic notes         Extract long-tail keywords
Fallback: 1 API if needed  Emergency API fallback only
     ↓
Final Output + Metadata Bundle
```

## Development Notes

### Critical Governance Rules
- **API Call Budget**: 7 total calls maximum per user prompt (2+1+2+1+0)
- **RAG Restriction**: Only Critic may perform external fact-checking
- **MVLM Enforcement**: Revisor + Summarizer are firebreaks against hallucination
- **Attribution Mandate**: Source + timestamp must persist through entire pipeline
- **No Loops**: Agents cannot retry beyond their allocated call limits
- **Connector-Only Policy**: Revisor/Summarizer may only add connecting words

### Voice Fingerprinting Implementation
- Lightweight frequency counts of collocations per corpus
- Tone scoring via fingerprint overlap calculation
- Separate profiles: Personal (conversational), Social (colloquial), Published (formal)
- Periodic fingerprint updates as new data is ingested

### Context Pack Schema
```json
{
  "snippet": "text content",
  "source": "Personal|Social|Published|External", 
  "date": "ISO-8601 timestamp",
  "tags": ["relevance", "keywords"],
  "voice_terms": ["collocation", "phrases"],
  "attribution": "source identifier",
  "notes": "selection reasoning"
}
```

### Failure Handling Patterns
- **Minor Fail**: Single threshold below target → rule-based local tweak
- **Major Fail**: Multiple thresholds missed → exactly 1 revise API call with delta prompt
- **Critical Fail**: Safety/truth/contradictory content → pipeline STOP + human review
- **Escalation**: Critic flags safety issues → terminate + audit log

### Testing Strategy
- Protocol and governance enforcement in `tests/`
- Agent pipeline tests with failure mode coverage
- Multi-corpus integration tests with attribution validation
- MVLM vs API fallback behavior verification

### Security & Attribution Requirements
- Never commit API keys or secrets to repository
- All PydanticAI tools wrapped with `SecureAgentTool` governance layer
- Structured logging with complete decision audit trails
- Metadata bundle preservation: attribution → change logs → keywords → final output