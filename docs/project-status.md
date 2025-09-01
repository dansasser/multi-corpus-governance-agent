# 📊 Project Status: Multi-Corpus Governance Agent

---

## 📌 Phase
**Phase Zero** – initial structure and scaffolding complete  

---

## 🎯 Current State
- Core specification files defined:
  - `agents.md`
  - `governance.md`
  - `routing-matrix.md`
  - `context-assembly.md`
  - Corpus search modules (`personal-search.md`, `social-search.md`, `published-search.md`)
- Documentation and diagrams scaffolded under `docs/`
- `src/mcg_agent/` directory established as code base location
- `tests/` folder present with placeholders

---

## 🚀 Next Objectives
Move directly into a **production-ready backend** (no MVP/mockups). Initial build must include:

- **Language & Frameworks**  
  - Python 3.11+  
  - **PydanticAI** for agent orchestration  

- **Database Layer**  
  - Secure connectors for SQLite/Postgres  
  - Migration tooling (Alembic or ORM migrations)  

- **Session & State Management**  
  - **Redis instance** for ephemeral session storage, job queues, and throttling  
  - TLS + AUTH-protected, with dangerous commands disabled (e.g., `FLUSHALL`)  
  - Redis used only for **volatile runtime state**, not as long-term source of truth  

- **Environment & Dependencies**  
  - Dependency pinning with `requirements.txt` (or `pip-tools` / `poetry`)  
  - Secure configuration management (`python-dotenv`, secrets handling, optional Vault integration)  

- **Governance & Logging**  
  - Guardrails from `governance.md` enforced at runtime  
  - Logging and attribution system with audit trails  
  - Corpus separation at DB level (personal, social, published isolated)  

- **Interfaces**  
  - Plan for API exposure (FastAPI with JWT or OAuth2)  
  - Strict request/response validation using Pydantic models  

---

## 🔒 Security Priorities from the Start
- Input validation on all agent calls (strict Pydantic schemas)  
- Redis secured with AUTH/TLS and limited ACLs  
- Corpus queries isolated with explicit connectors  
- External retrieval (RAG/web) only through logged + attributed calls  
- No unsecured endpoints or debug code in production builds  
- Early planning for secrets rotation and CI/CD hardening  

---

## 📅 Roadmap
- **Phase Zero** → Establish scaffolding + definitions ✅  
- **Phase One** → Implement core backend with PydanticAI, DB connectors, Redis session management, logging, and baseline security  
- **Phase Two** → Add RAG extension for Published/Social, external tool integrations (e.g., Twilio/Realtime API)  
- **Phase Three** → Deployment hardening (Docker, CI/CD, secrets rotation, monitoring)  

---

## ⚠️ Risks / Notes
- Security must be enforced **in early code commits** — no “fix later” assumption  
- Redis must not become a shadow database (ephemeral state only)  
- Governance rules require runtime tests to prevent bypass  
- Must balance speed (usable assistant early) with safety (production-grade baseline)  

---
