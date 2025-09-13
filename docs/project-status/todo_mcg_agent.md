# MCG Agent – Production Readiness TODOs (No MVLM/external corpora)

This checklist captures concrete tasks to make the system production‑ready without relying on MVLM or external (social/published) corpora. It also includes a swappable text‑generation provider to use OpenAI in dev and MVLM later.

## 0) Swappable Text Generation Provider (Dev ↔ MVLM)
- [x] Define provider interface: `TextGenerationProvider` (generate, revise, summarize)
- [x] Implement `OpenAIProvider` (dev mode) with settings/env keys and rate‑limit/backoff
- [x] Adapt `mvlm/provider.py` to a small factory that chooses: `OpenAIProvider` vs. `MVLMProvider`
- [x] Wire routing pipeline Revisor/Summarizer to use provider interface (no other code changes)
- [x] Add settings flags: `GEN_PROVIDER={openai|mvlm}`, `OPENAI_MODEL`, `OPENAI_API_KEY`
- [ ] Tests: stub OpenAI calls and assert pipeline paths, error handling, and governance logs

## 1) Response Optimizer (Non‑MVLM)
- [x] Create `optimizer/response_optimizer.py` with strategies scaffold (balanced default)
- [ ] Parallelize independent steps (e.g., analysis/validation) with asyncio gather
- [x] Add timebox and fallback behavior
- [x] Add response cache (TTL) keyed on prompt + context hash; store metadata for attribution
- [x] Metrics: strategy usage, latency per strategy, cache hits/misses
- [x] Governance: ensure optimizer doesn’t elevate RAG or cross role permissions
- [x] Wire into Revisor/Summarizer behind `FEATURE_RESPONSE_OPTIMIZER`

## 2) Cache Upgrade (Voice Patterns/Response Cache)
- [x] Extend `utils/cache.py` with local LRU (thread‑safe) option and optional compression (zlib)
- [x] Add counters: hits, misses, evictions; gauges: size, items, approx bytes
- [x] Background cleanup task for expired entries (daemon thread)
- [x] Expose cache metrics via Prometheus (labels: namespace/backend)
- [x] Document operational knobs in `.env.example`

## 3) Memory Manager (Lightweight)
- [x] Add `utils/memory_manager.py` (psutil‑based) to read RSS/percent
- [x] Thresholds: warn/limit; structured logs (metrics optional later)
- [ ] Soft signals to caches/optimizer to tighten TTL or switch to speed strategy under pressure
- [x] Health endpoint augmentation with memory summary

## 4) Monitoring & Logging Enhancements
- [x] Request/task correlation IDs bound via contextvars and returned in /query metadata
- [x] Per‑stage latency histogram + governance denial counter (pipeline)
- [ ] Stage success/fail counters and summarized stats
- [ ] Optional Sentry init guarded by DSN; scrub sensitive fields
- [ ] README update for /metrics exposure and key series

## 5) Container Hardening
- [ ] Multi‑stage Dockerfile: builder/runtime, non‑root, minimal OS pkgs
- [ ] `entrypoint.sh`: env validation, wait‑for‑deps, alembic upgrade, graceful signals
- [ ] `healthcheck.sh`: DB ping, /health, memory thresholds; used by Docker HEALTHCHECK
- [ ] Compose updates: use entrypoint, environment via .env, bind mounts minimized

## 6) Kubernetes Scaffolding (Optional now, ready later)
- [ ] Base manifests: Namespace, ConfigMap, Secret, Deployment, Service, Ingress
- [ ] Probes: startup/liveness/readiness; resource requests/limits; non‑root securityContext
- [ ] Prometheus annotations; ingress headers (rate limit, gzip); TLS notes

## 7) Voice QA Tightening (Deterministic)
- [ ] Replace TODO scoring with deterministic rules for tone/style consistency
- [ ] Emit QA metrics; gate “quality_mode” of optimizer using QA scores
- [ ] Docs on how QA interacts with governance (no new corpus fetches in restricted roles)

## 8) CLI and Docs
- [ ] `mcg-agent query` printing options (json/markdown), include request_id/task_id inline
- [ ] Import/export docs for personal corpus; API usage examples
- [x] Update `.env.example` with new provider/optimizer/cache/memory settings

---

## Pick Up Here (When You Return)
1) Wire soft‑pressure from MemoryManager into optimizer/cache
   - [x] Force optimizer `strategy=speed` under pressure and bypass cache
   - [x] Metric for “pressure mode” activations
   - [ ] Optionally reduce TTLs instead of bypassing cache (nice-to-have)
2) Monitoring polish
   - [x] Add stage success/failure counters
   - [x] Add README section for metrics and correlation fields
   - [ ] Optional endpoint to summarize recent pipeline runs
3) Container hardening
   - Multi‑stage Dockerfile + entrypoint + healthcheck; integrate Docker HEALTHCHECK.
4) Optional: K8s base manifests
   - Namespace, ConfigMap/Secret, Deployment/Service/Ingress with probes + securityContext.

## Completed in this pass
- Container hardening (multi-stage Dockerfile, non-root, entrypoint, healthcheck, compose uses entrypoint)
- Pipeline summary endpoint: `GET /pipeline/summary` returns in-memory stage success/fail counts
- Kubernetes scaffolding: docs/ops/k8s (namespace, configmap, secret.example, deployment, service, ingress)
- JWT auth on critical endpoints (`/query`, `/pipeline/summary`) and CLI token minting
- Deterministic Voice QA + optimizer quality gating (configurable thresholds, optional enforcement)
- Sentry integration (opt-in via DSN) with header/user scrubbing
- Auth + QA/optimizer tests added
- README/API docs updated (auth, endpoints, metrics, provider swap, optimizer config)

## Pick Up Tomorrow
1) Tests & hardening
   - Expand provider swap tests (OpenAI stub), memory pressure behavior, and pipeline happy-path.
   - Optional: reduce TTLs under pressure (instead of bypassing cache) + tests.
2) K8s/CI polish
   - Set image name, add HPA/PDB, secure `/metrics` via Ingress, add CI build/publish and tests.
3) Voice QA refinements
   - More nuanced rules; tie to voice profile when available; add metrics breakdowns.
4) CLI polish
   - Default printing of request_id/task_id, add headers example for API calls.

## Then Next
- Voice QA determinism and gating (feed into optimizer “quality” strategy).
- Sentry wiring (guarded by DSN) and sanitization.
- CLI improvements (show request_id/task_id inline, markdown output option).
- Tests for provider swap and optimizer behavior (OpenAI stub; timebox paths).

## Notes
- Dev swap works now: set `GEN_PROVIDER=openai` (with `OPENAI_API_KEY`) to test without MVLM.
- Optimizer is feature‑flagged: set `FEATURE_RESPONSE_OPTIMIZER=true` to enable.

---

## Deliverables Checklist
- [ ] Provider interface + OpenAI provider + factory wiring
- [ ] Response Optimizer with strategies, cache, metrics
- [ ] Cache upgrade with metrics and cleanup
- [ ] Memory manager with thresholds and metrics
- [ ] Monitoring/logging enhancements + Sentry optional
- [ ] Container hardening (multi‑stage, entrypoint, healthcheck)
- [ ] K8s scaffolding (base manifests)
- [ ] Voice QA determinism + metrics
- [ ] CLI/docs updates
