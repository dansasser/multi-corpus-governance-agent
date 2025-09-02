# Agents

## 📌 Purpose

This file is the **orientation guide for coding agents** working on the Multi-Corpus Governance Agent.
It describes the project’s intent, the expected environment, coding conventions, and where to find detailed rules.

---

## 🛠 Tech Stack

* **Language**: Python 3.11+
* **Framework**: [PydanticAI](https://docs.pydantic.dev/latest/ai/) + [FastAPI](https://fastapi.tiangolo.com/)
* **Core Libraries**:

  * `pydantic-ai` → agent orchestration
  * `fastapi` → REST API server ✅ **IMPLEMENTED**
  * `uvicorn` + `gunicorn` → ASGI server for production
  * `httpx` → async HTTP client
  * `sqlalchemy` → database ORM ✅ **IMPLEMENTED**  
  * `redis` → session management and caching ✅ **IMPLEMENTED**
  * `PyJWT` → JSON Web Token authentication ✅ **IMPLEMENTED**
* **Database**: SQLite (dev) / PostgreSQL (production)
* **Authentication**: JWT with Redis session management ✅ **IMPLEMENTED**
* **Monitoring**: Health checks, metrics, and governance violation tracking ✅ **IMPLEMENTED**
* **Containerization**: Docker (future)

---

## 📂 Key Documents

* [`governance.md`](./governance.md) → defines **roles, guardrails, outputs**.
* [`routing-matrix.md`](./routing-matrix.md) → defines **flow, thresholds, and fail/stop rules**.
* [`context-assembly.md`](./context-assembly.md) → defines **multi-corpus retrieval, voice fingerprinting, scoring, and logs**.

Each agent must respect these rules. No shortcuts.

---

## 🚀 Setup

### 1. Clone the repo

```bash
git clone https://github.com/dansasser/multi-corpus-governance-agent.git
cd multi-corpus-governance-agent
```

### 2. Create environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

*(requirements.txt will include `pydantic-ai`, `fastapi`, `httpx`, etc.)*

### 4. Environment variables

Create a `.env` file with:

```
OPENAI_API_KEY=your-key
DATABASE_URL=sqlite:///./db.sqlite3
```

---

## ▶️ Usage

### Database Initialization

```bash
# Initialize database with migrations and optional seed data
./scripts/init-db.sh --seed
```

### Development Server

```bash
# Start development server with hot reload
./scripts/start-dev.sh

# Alternative: Use CLI tool
mcg-agent serve --reload

# Alternative: Direct uvicorn
uvicorn src.mcg_agent.api.app:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **Main API**: `http://localhost:8000`
- **Interactive Docs**: `http://localhost:8000/docs` 
- **Health Check**: `http://localhost:8000/health`

### Production Server

```bash
# Start production server with Gunicorn
./scripts/start-prod.sh

# Alternative: Use CLI with multiple workers  
mcg-agent serve --workers 4
```

### Testing

```bash
# Run comprehensive test suite
./scripts/run-tests.sh

# Run specific test types
./scripts/run-tests.sh --unit          # Unit tests only
./scripts/run-tests.sh --integration   # Integration tests only
./scripts/run-tests.sh --api          # API tests only
./scripts/run-tests.sh --fast         # Fast mode (no coverage)

# Alternative: Direct pytest
pytest tests/ -v --cov=src/mcg_agent
```

### Health Monitoring

```bash
# Check system health
./scripts/health-check.sh --verbose

# Check health with different output formats
./scripts/health-check.sh --format json
./scripts/health-check.sh --format prometheus

# Monitor specific endpoint
curl http://localhost:8000/health
```

### Code Quality

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

---

## 🚦 Workflow Summary

1. **User prompt** enters via API or CLI.
2. **Context Assembly** builds the context pack.
3. **Routing Matrix** passes it through Ideator → Drafter → Critic → Revisor → Summarizer.
4. **Output** is returned with attribution and logs.

---

## 📏 Conventions

* **Type Safety**: Always use `pydantic.BaseModel`.
* **Naming**:

  * Agents: `IdeatorAgent`, `DrafterAgent`, etc.
  * Modules: lowercase with underscores.
* **Docs-first**: Code must reference relevant `.md` files.
* **No hardcoding**: Configurations pulled from `.env` or `settings.py`.

---

## 🔐 Security & Constraints

* API keys injected via environment variables.
* No raw SQL — ORM or parameterized queries only.
* No bypassing governance checks.
* Attribution and logging are mandatory.

---

## ✅ Checklist for Agents

* [ ] Reads `governance.md` rules before execution.
* [ ] Routes correctly per `routing-matrix.md`.
* [ ] Uses context packs from `context-assembly.md`.
* [ ] Logs every decision with attribution.

---

Here’s an **expanded `agents.md` with a “Future Work” section**, so both coding agents and contributors see the roadmap:

---

# Agents.md

## 📌 Purpose

This file is the **orientation guide for coding agents** working on the Multi-Corpus Governance Agent.
It describes the project’s intent, expected environment, coding conventions, and where to find detailed rules.

---

## 🛠 Tech Stack

* **Language**: Python 3.11+
* **Framework**: [PydanticAI](https://docs.pydantic.dev/latest/ai/)
* **Core Libraries**:

  * `pydantic-ai` → agent orchestration
  * `fastapi` → serving APIs (planned)
  * `httpx` → HTTP calls (planned)
  * `sqlalchemy` → database layer (planned)
* **Database**: SQLite (dev) / Postgres (prod option)
* **Containerization**: Docker (future)

---

## 📂 Key Documents

* [`governance.md`](./governance.md) → defines roles, guardrails, outputs.
* [`routing-matrix.md`](./routing-matrix.md) → flow, thresholds, fail/stop rules.
* [`context-assembly.md`](./context-assembly.md) → multi-corpus retrieval, voice fingerprints, scoring, and logs.

---

## 🔍 Corpus Search Modules

Each agent may query corpora through well-defined search modules:

- [`personal-search.md`](./personal-search.md) → DB-only access (chat history, notes, drafts).  
- [`social-search.md`](./social-search.md) → DB + RAG hybrid (short-form posts, hashtags, engagement).  
- [`published-search.md`](./published-search.md) → DB + RAG hybrid (articles, blogs, research).  

### Access Rules
- **Ideator** → may call all three; RAG allowed for Social/Published only if coverage gaps.  
- **Drafter** → may use Personal + Social for tone anchoring; no RAG.  
- **Critic** → full access; always permitted to invoke RAG.  
- **Revisor** → no new queries; works with provided snippets.  
- **Summarizer** → no queries.  

---

## 🚀 Setup

### Automated Setup (Recommended)

```bash
git clone https://github.com/dansasser/multi-corpus-governance-agent.git
cd multi-corpus-governance-agent
./scripts/setup.sh
```

This script will:
- Create and activate virtual environment
- Install all dependencies (FastAPI, authentication, database tools)
- Validate database and Redis connections
- Generate `.env` template with security placeholders

### Manual Setup

```bash
# Clone the repository
git clone https://github.com/dansasser/multi-corpus-governance-agent.git
cd multi-corpus-governance-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies with development tools
pip install -e .[dev]

# Or production only
pip install -e .
```

### Environment Variables

Create `.env` with:

```bash
# Database Configuration
DATABASE_URL=sqlite:///./mcg_agent.db

# Redis Configuration (session management)
REDIS_URL=redis://localhost:6379/0

# Security Keys (generate secure values!)
JWT_SECRET_KEY=your-jwt-secret-key-here
ENCRYPTION_KEY=your-32-byte-encryption-key

# API Keys
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key

# Server Configuration
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
```

---

## ▶️ Usage

### Database Initialization

```bash
# Initialize database with migrations and optional seed data
./scripts/init-db.sh --seed
```

### Development Server

```bash
# Start development server with hot reload
./scripts/start-dev.sh

# Alternative: Use CLI tool
mcg-agent serve --reload

# Alternative: Direct uvicorn
uvicorn src.mcg_agent.api.app:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **Main API**: `http://localhost:8000`
- **Interactive Docs**: `http://localhost:8000/docs` 
- **Health Check**: `http://localhost:8000/health`

### Production Server

```bash
# Start production server with Gunicorn
./scripts/start-prod.sh

# Alternative: Use CLI with multiple workers  
mcg-agent serve --workers 4
```

### Testing

```bash
# Run comprehensive test suite
./scripts/run-tests.sh

# Run specific test types
./scripts/run-tests.sh --unit          # Unit tests only
./scripts/run-tests.sh --integration   # Integration tests only
./scripts/run-tests.sh --api          # API tests only
./scripts/run-tests.sh --fast         # Fast mode (no coverage)

# Alternative: Direct pytest
pytest tests/ -v --cov=src/mcg_agent
```

### Health Monitoring

```bash
# Check system health
./scripts/health-check.sh --verbose

# Check health with different output formats
./scripts/health-check.sh --format json
./scripts/health-check.sh --format prometheus

# Monitor specific endpoint
curl http://localhost:8000/health
```

### Code Quality

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

---

## 🚦 Workflow Summary

1. User prompt enters system.
2. Context Assembly builds the context pack.
3. Routing Matrix passes through Ideator → Drafter → Critic → Revisor → Summarizer.
4. Output returned with attribution and logs.

---

## 📏 Conventions

* Use `pydantic.BaseModel` for type safety.
* Agents named `IdeatorAgent`, `DrafterAgent`, etc.
* Modules: lowercase with underscores.
* Configs pulled from `.env` or `settings.py`.
* Code must reference the `.md` files where applicable.

---

## 🔐 Security & Constraints

* API keys in environment variables only.
* No raw SQL.
* Governance checks mandatory.
* Attribution and logging are non-optional.

---

## ✅ Checklist for Agents

* [ ] Reads `governance.md` rules before execution.
* [ ] Routes correctly per `routing-matrix.md`.
* [ ] Uses context packs from `context-assembly.md`.
* [ ] Logs every decision with attribution.

---

## 🌐 FastAPI Integration ✅ **IMPLEMENTED**

The MCG Agent now includes a complete REST API with the following endpoints:

### Authentication & Security
- `POST /auth/login` - User authentication with JWT tokens
- `POST /auth/logout` - Session termination and token revocation 
- `POST /auth/refresh` - JWT token refresh
- `GET /auth/me` - Current user profile
- Middleware for request logging, security headers, and governance enforcement

### Agent Pipeline Endpoints  
- `POST /agents/pipeline/execute` - Execute complete five-agent pipeline
- `POST /agents/ideator` - Run Ideator agent individually
- `POST /agents/drafter` - Run Drafter agent individually
- `POST /agents/critic` - Run Critic agent individually
- `POST /agents/revisor` - Run Revisor agent individually
- `POST /agents/summarizer` - Run Summarizer agent individually
- `GET /agents/corpus/query` - Query multi-corpus data with access control

### Health & Monitoring
- `GET /health` - Comprehensive system health check
- `GET /health/live` - Kubernetes liveness probe
- `GET /health/ready` - Kubernetes readiness probe
- `GET /monitoring/metrics` - System performance metrics
- `GET /monitoring/violations` - Governance violation tracking

All endpoints include:
- **JWT Authentication** with Redis session management
- **Request validation** using Pydantic models
- **Governance enforcement** at the API layer
- **Comprehensive logging** for audit trails
- **Error handling** with proper HTTP status codes

---

## 🌱 Future Work

* **Containerization**: Dockerfile + docker-compose for reproducible environments.
* **CI/CD**: GitHub Actions for linting, tests, and builds.
* **Web Interface**: React/Vue frontend for the FastAPI backend.
* **Real-time Features**: WebSocket support for live agent pipeline monitoring.
* **Corpus Expansion**: Add connectors for external APIs and additional data sources.
* **MVLM Variants**: Experiment with specialized Minimum Viable Language Models for different tones/domains.
* **Interactive Interfaces**: Real-time voice integration (Twilio + OpenAI Realtime API).
* **Deployment Targets**: Initial cloud deployment via DigitalOcean / Fly.io, with Kubernetes as a scaling option.
* **Performance**: Caching layer, connection pooling, and horizontal scaling.

---

