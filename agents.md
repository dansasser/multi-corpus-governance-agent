# Agents

## 📌 Purpose

This file is the **orientation guide for coding agents** working on the Multi-Corpus Governance Agent.
It describes the project’s intent, the expected environment, coding conventions, and where to find detailed rules.

---

## 🛠 Tech Stack

* **Language**: Python 3.11+
* **Framework**: [PydanticAI](https://docs.pydantic.dev/latest/ai/)
* **Core Libraries**:

  * `pydantic-ai` → agent orchestration
  * `fastapi` → serving APIs (planned)
  * `httpx` → HTTP calls (planned)
  * `sqlalchemy` → database layer (optional, planned)
* **Database**: SQLite (dev) / Postgres (production option)
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

### Run dev server

```bash
uvicorn app.main:app --reload
```

### Run tests

```bash
pytest tests/
```

### Lint & format

```bash
black .
ruff check .
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

## 🚀 Setup

### Clone the repo

```bash
git clone https://github.com/your-org/multi-corpus-governance-agent.git
cd multi-corpus-governance-agent
```

### Create environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Environment variables

Create `.env`:

```
OPENAI_API_KEY=your-key
DATABASE_URL=sqlite:///./db.sqlite3
```

---

## ▶️ Usage

### Run dev server

```bash
uvicorn app.main:app --reload
```

### Run tests

```bash
pytest tests/
```

### Lint & format

```bash
black .
ruff check .
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

## 🌱 Future Work

* **Containerization**: Dockerfile + docker-compose for reproducible environments.
* **CI/CD**: GitHub Actions for linting, tests, and builds.
* **Monitoring**: Structured logs exported to Grafana/Prometheus.
* **Corpus Expansion**: Add connectors for external APIs and additional data sources.
* **MVLM Variants**: Experiment with specialized Minimum Viable Language Models for different tones/domains.
* **Interactive Interfaces**: Real-time voice integration (Twilio + OpenAI Realtime API).
* **Deployment Targets**: Initial cloud deployment via DigitalOcean / Fly.io, with Kubernetes as a scaling option.

---

