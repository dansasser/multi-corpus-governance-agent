# Temporary Stubs and Replacement Plan

This repository aims for production readiness. A few components are currently
stubbed to unblock parallel implementation. Each stub is documented below with
its replacement plan and acceptance criteria.

1) Search Connectors (DB-backed)
- Files: `src/mcg_agent/search/connectors.py`
- Current: SQLAlchemy-based queries against ORM models; ranking is simplified
  (recency/engagement/authority). If DB is unconfigured/empty, returns empty
  results without stubs.
- Next: Add Postgres FTS ranking (to_tsvector/to_tsquery, ts_rank_cd) via
  SQLAlchemy expressions; add logging of scores and attribution; seed fixtures
  and integration tests.

2) GovernedAgentPipeline Execution (stub)
- Files: `src/mcg_agent/routing/pipeline.py`
- Current: Placeholder `execute_agent_stage` echoes content.
- Replace with: PydanticAI agents (Ideator/Drafter/Critic/Revisor/Summarizer),
  secure tools, API call governance, revise-call flow, and metadata propagation.
- Acceptance: Pipeline exercises agents in order, enforces limits, logs audit,
 and produces `MetadataBundle`.

7) Ideator Agent Orchestration (local mode)
- Files: `src/mcg_agent/agents/ideator.py`, `src/mcg_agent/routing/pipeline.py`
- Status: `run_ideator_local` invokes PydanticAI-registered tools with governance
  under the Ideator role to assemble a ContextPack deterministically (no LLM).
- Future: Add optional `IdeatorAgent` (LLM-driven) that uses the same tools and
  applies scoring and revise-call when model guidance is desired.

3) Call Tracker Backend (memory default)
- Files: `src/mcg_agent/governance/call_tracker.py`
- Current: In-memory counter with asyncio lock; Redis-backed optional planned.
- Replace with: Redis-backed atomic counters (TLS+AUTH) selectable via env
  `MCG_CALL_TRACKER_BACKEND=redis`.
- Acceptance: Atomic INCR/GET per `(agent, task)`; TTL per task; tested under
  concurrency; governance violations logged.

4) WAF Integration (stub)
- Files: `src/mcg_agent/security/waf_integration.py`
- Current: Simple IP allowlist and incident print.
- Replace with: Integration with external WAF/gateway (Cloudflare/AWS WAF) and
  metrics/log sinks; denial reasons enumerated.
- Acceptance: Requests filtered per policy; incidents shipped to audit sink; e2e tests.

5) Governance Validator (minimal checks)
- Files: `src/mcg_agent/security/governance_enforcer.py`
- Current: Minimal role and content checks.
- Replace with: Full validation against thresholds (tone, coverage, diversity),
  RAG access, and failure patterns (minor/major/critical).
- Acceptance: Unit tests for all failure paths; revise-call invoked per routing-matrix.

6) PydanticAI Tool Shim (test-only convenience)
- Files: `src/mcg_agent/search/tools.py`
- Current: Fallback `tool` decorator if `pydantic_ai` missing.
- Replace with: Require `pydantic_ai` in runtime; remove shim in production build.
- Acceptance: Tools registered and enforced by PydanticAI; shim removed.

All stubs are temporary and tracked in the plan. Replacement will be completed
before any production deployment tag is cut.
