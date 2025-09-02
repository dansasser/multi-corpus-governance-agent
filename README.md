# 📚 Multi-Corpus Governance Agent

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE.md)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/) 
[![PydanticAI](https://img.shields.io/badge/powered%20by-PydanticAI-green)](https://docs.pydantic.dev/latest/ai/)
[![Docker](https://img.shields.io/badge/docker-image-blue?logo=docker)](https://hub.docker.com/r/your-org/multi-corpus-governance-agent)
[![License: Commercial](https://img.shields.io/badge/License-Commercial-red.svg)](LICENSE.md)
[![Governance](https://img.shields.io/badge/Governance-Multi--Agent-green.svg)](governance.md)
[![Docs](https://img.shields.io/badge/Docs-README-lightgrey.svg)](README.md)
[![Status](https://img.shields.io/badge/Status-Phase%20One%20Complete-green.svg)](#)
[![Security Policy](https://img.shields.io/badge/Security-Policy-yellow.svg)](SECURITY.md)
[![Contributions Welcome](https://img.shields.io/badge/Contributions-Welcome-brightgreen.svg)](CONTRIBUTING.md)


A governed AI assistant that connects to multiple corpora (personal, social, published) and routes them through a **five-agent pipeline**: Ideator → Drafter → Critic → Revisor → Summarizer.

Unlike prompt-tuned chatbots, reasoning and validation are handled in the **governance layer**. Heavy lifting (idea generation, drafting, validation) uses API backends, while **Minimum Viable Language Models (MVLMs)** act as firebreaks at the end of the chain to enforce tone, reduce noise, and package results.

This design produces **accurate, auditable, and voice-aligned outputs** that can scale from content writing to chat answering and eventually real-time voice or telephony integration.

---

## ✨ Features

* 🔗 **Multi-corpus retrieval** from Personal, Social, and Published data.
* 🧩 **Five-agent governance pipeline** for checks and balances.
* 🔍 **Critic with full RAG powers** to validate truth, accuracy, and SEO.
* 🛡 **MVLM firebreaks** (Revisor + Summarizer) to lock tone and prevent drift.
* 📊 **Metadata logging**: attribution, long-tail keywords, change logs, and token usage.
* 🗣 **Persona alignment** for consistent voice across chat, writing, and publishing.
* 🌐 **FastAPI Integration**: Production-ready REST API with authentication and monitoring.
* 🔐 **JWT Authentication**: Secure session management with Redis backend.
* 📈 **Health Monitoring**: Kubernetes-ready health checks and system metrics.
* 🚀 **Production Ready**: Complete deployment scripts and configuration.

---

## 🗂 Quick Reference

| **Role**       | **Inputs**                             | **Tools**                              | **Responsibilities**                            | **Outputs**                           |
| -------------- | -------------------------------------- | -------------------------------------- | ----------------------------------------------- | ------------------------------------- |
| **Ideator**    | User prompt, multi-corpus snippets     | API (1–2 calls), corpora               | Outline ideas, tone/coverage scoring, annotate  | Structured outline + notes            |
| **Drafter**    | Ideator outline + notes, voice samples | API (1 call), limited corpora          | Expand outline into draft, apply SEO + style    | Draft + metadata (voice/SEO samples)  |
| **Critic**     | Draft + outline, corpora, governance   | API (≤2 calls), corpora, RAG           | Voice, truth, SEO, safety checks, annotate      | Feedback notes + optional corrections |
| **Revisor**    | Drafter draft + Critic notes, corpora  | MVLM (preferred), limited API, corpora | Apply Critic’s notes, preserve tone, fix errors | Corrected draft + change log          |
| **Summarizer** | Revisor draft + metadata               | MVLM (preferred), API fallback         | Condense/package, extract long-tail keywords    | Summary + metadata (keywords, trims)  |

---

## 📁 Directory Structure

```
/multi-corpus-governance-agent
│
├── agents.md
├── governance.md
├── routing-matrix.md
├── context-assembly.md
├── personal-search.md
├── social-search.md
├── published-search.md
│
├── docs/               # long-form documentation, articles
│    └── diagrams/           # DOT + PNG + TXT diagrams
├── tests/              # unit and integration tests
│
└── src/                # 🔑 all runnable Python code
    └── mcg_agent/      # your package namespace
        ├── __init__.py
        ├── main.py     # entrypoint (FastAPI app or CLI)
        ├── api/        # 🌐 FastAPI application and routers
        │   ├── app.py      # main FastAPI application
        │   ├── auth.py     # authentication middleware
        │   └── routers/    # API endpoint routers
        │       ├── auth.py      # authentication endpoints
        │       ├── health.py    # health monitoring endpoints
        │       ├── agents.py    # five-agent pipeline API
        │       └── monitoring.py # security & compliance monitoring
        ├── auth/       # 🔐 JWT authentication and session management
        ├── agents/     # Ideator, Drafter, Critic, Revisor, Summarizer
        ├── search/     # connectors: personal, social, published
        ├── governance/ # enforcement rules, scoring, guardrails
        ├── database/   # 🗄️ database models, migrations, connections
        ├── cli/        # 💻 command-line interface tools
        └── utils/      # logging, attribution, shared helpers
```

---

## 🌐 FastAPI Endpoints

The MCG Agent provides a comprehensive REST API for interacting with the five-agent pipeline:

### Authentication Endpoints
- `POST /auth/login` - User authentication with JWT tokens
- `POST /auth/logout` - Session termination and token revocation
- `POST /auth/refresh` - JWT token refresh
- `POST /auth/register` - User registration
- `GET /auth/me` - Current user profile

### Agent Pipeline Endpoints
- `POST /agents/pipeline/execute` - Execute complete five-agent pipeline
- `POST /agents/ideator` - Run Ideator agent individually
- `POST /agents/drafter` - Run Drafter agent individually
- `POST /agents/critic` - Run Critic agent individually
- `POST /agents/revisor` - Run Revisor agent individually
- `POST /agents/summarizer` - Run Summarizer agent individually
- `GET /agents/corpus/query` - Query multi-corpus data with access control

### Health & Monitoring Endpoints
- `GET /health` - Comprehensive system health check
- `GET /health/live` - Kubernetes liveness probe
- `GET /health/ready` - Kubernetes readiness probe
- `GET /health/ping` - Basic connectivity check
- `GET /monitoring/metrics` - System performance metrics
- `GET /monitoring/violations` - Governance violation tracking
- `GET /monitoring/usage` - API usage analytics

### Development & Production Scripts
- `./scripts/start-dev.sh` - Start development server with hot reload
- `./scripts/start-prod.sh` - Start production server with Gunicorn
- `./scripts/init-db.sh` - Initialize database and run migrations
- `./scripts/run-tests.sh` - Comprehensive test suite with coverage
- `./scripts/health-check.sh` - Health monitoring script

---

## 📈 Sequence Flow

```
User Prompt
    |
    v
+----------------+
| Classification |
+----------------+
        |
        v
+-----------------+
| Routing Matrix  |-----> Multi-Corpus Retrieval (Personal | Social | Published)
+-----------------+
        |
        v
+-------------------+
| Context Assembly  |
+-------------------+
        |
        v
+-------------------+
|      Ideator      |---(API + corpora, 1–2 calls, tone check)
+-------------------+
        |
        v
+-------------------+
|      Drafter      |---(API + limited corpora, 1 call)
+-------------------+
        |
        v
+-------------------+
|      Critic       |---(API + corpora + RAG, ≤2 calls, full check)
+-------------------+
        |
        v
+-------------------+
|      Revisor      |---(MVLM, corpus, API fallback once)
+-------------------+
        |
        v
+-------------------+
|    Summarizer     |---(MVLM only, API fallback optional)
+-------------------+
        |
        v
+-------------------+
|   Final Output    |---(Chat reply, Draft+Brief, Metadata)
+-------------------+
```

---

## 🗄 Metadata Flow

```
Routing + Corpora Pull
        |
        v
 Attribution ───────► Voice Samples ───────► Corpus Metadata
        |                                  |
        v                                  v
   Ideator → Drafter → Critic → Revisor → Summarizer
        |
        v
   Change Logs ───► Long-tail Keywords ───► Tone/SEO Flags
        |
        v
   Final Output + Metadata Bundle
```

---

## 📝 Metadata Schema

```json
{
  "task_id": "string",
  "role": "string",
  "input_sources": [
    {
      "corpus": "Personal|Social|Published",
      "snippet_id": "string",
      "source_text": "string",
      "timestamp": "ISO-8601"
    }
  ],
  "attribution": [
    {
      "claim_id": "string",
      "source": "string",
      "timestamp": "ISO-8601"
    }
  ],
  "tone_flags": {
    "voice_match_score": "float",
    "seo_keywords": ["string"],
    "safety_flags": ["string"]
  },
  "change_log": [
    {
      "change_id": "string",
      "original_text": "string",
      "revised_text": "string",
      "reason": "string",
      "applied_by": "Critic|Revisor"
    }
  ],
  "long_tail_keywords": ["string"],
  "token_stats": {
    "input_tokens": "int",
    "output_tokens": "int"
  },
  "trimmed_sections": ["string"],
  "final_output": "string"
}
```

---

## ⚖️ Governance Rules

* Only **Ideator, Drafter, Critic** may call APIs.
* Only **Critic** may use RAG.
* **Revisor + Summarizer** must use MVLMs as default.
* No role may loop original prompts. Max two API calls per role.
* All outputs must preserve attribution.
* Revisor and Summarizer may only add connector tokens (and, the, commas).
* Summarizer must extract long-tail keywords, logged even if hidden.

---

## 🚀 Roadmap

* [x] **Phase 1**: FastAPI integration with authentication, health monitoring, and agent pipeline API.
* [ ] **Phase 2**: Writing assistant + chat answering with web interface.
* [ ] **Phase 3**: Real-time voice with OpenAI Realtime API.
* [ ] **Phase 4**: Telephony integration (Twilio).
* [ ] **Phase 5**: Expand MVLMs for multiple personas (neutral, casual, worldview).

## 🏃‍♂️ Quick Start

### 1. Setup Environment
```bash
git clone https://github.com/dansasser/multi-corpus-governance-agent.git
cd multi-corpus-governance-agent
./scripts/setup.sh
```

### 2. Configure Environment
```bash
# Copy and edit .env file
cp .env.example .env
# Edit .env with your database URL, Redis URL, and API keys
```

### 3. Initialize Database
```bash
./scripts/init-db.sh --seed
```

### 4. Start Development Server
```bash
./scripts/start-dev.sh
```

The API will be available at `http://localhost:8000` with interactive documentation at `http://localhost:8000/docs`.

### 5. Run Tests
```bash
./scripts/run-tests.sh
```

### 6. Health Check
```bash
./scripts/health-check.sh --verbose
```

---

## 💡 Use Cases

* ✍️ Draft LinkedIn posts or blog entries in your exact voice.
* 💬 Deploy as a chatbot on your site with governance filters.
* 📞 Extend to real-time answering with voice APIs.
* 🔒 Maintain consistent tone, accuracy, and attribution across all channels.

---

## 🌟 Contributing

Contributions are welcome! Please open issues and PRs to improve documentation, expand connectors, or refine governance rules.

