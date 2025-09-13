from __future__ import annotations

from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, Field

from mcg_agent.config import get_settings, validate_environment
from mcg_agent.db.session import get_session
from mcg_agent.routing.pipeline import GovernedAgentPipeline
from mcg_agent.utils.logging import setup_logging, get_logger
from mcg_agent.utils.memory_manager import MemoryManager
from mcg_agent.security.jwt_auth import get_current_user
from fastapi import Depends
from mcg_agent.utils.pipeline_stats import PipelineStats

# Optional Prometheus metrics
try:  # pragma: no cover - optional dependency
    from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
except Exception:  # pragma: no cover
    Counter = None  # type: ignore
    Histogram = None  # type: ignore
    generate_latest = None  # type: ignore
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4"

import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars, get_contextvars
from uuid import uuid4


setup_logging()
logger = get_logger("api")
app = FastAPI(title="MCG Agent API", version="0.1.0")

# Metrics
_settings = get_settings()
# Optional Sentry initialization (guarded by DSN)
try:  # pragma: no cover
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration

    if _settings.monitoring.SENTRY_DSN:
        def _before_send(event, hint):
            # Scrub Authorization header and keep only user id
            req = event.get("request") if isinstance(event.get("request"), dict) else None
            if req and isinstance(req.get("headers"), dict):
                headers = req["headers"]
                for k in list(headers.keys()):
                    if k.lower() == "authorization":
                        headers[k] = "[REDACTED]"
            if "user" in event and isinstance(event["user"], dict):
                event["user"] = {k: v for k, v in event["user"].items() if k in {"id"}}
            return event

        sentry_sdk.init(
            dsn=_settings.monitoring.SENTRY_DSN,
            integrations=[FastApiIntegration()],
            environment=_settings.monitoring.SENTRY_ENVIRONMENT or _settings.server.ENVIRONMENT,
            traces_sample_rate=0.0,
            before_send=_before_send,
        )
        logger.info("sentry_initialized", environment=_settings.server.ENVIRONMENT)
except Exception as _e:  # pragma: no cover
    logger.info("sentry_not_initialized", reason=str(_e))
if Counter and Histogram:  # pragma: no cover
    REQS = Counter(
        "mcg_pipeline_requests_total",
        "Total pipeline requests",
        labelnames=("endpoint", "status"),
    )
    LATENCY = Histogram(
        "mcg_pipeline_latency_seconds",
        "Pipeline processing latency",
        buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0),
        labelnames=("endpoint",),
    )
else:
    REQS = None  # type: ignore
    LATENCY = None  # type: ignore


class QueryRequest(BaseModel):
    prompt: str = Field(..., description="User prompt to process")


class QueryResponse(BaseModel):
    task_id: str
    agent_role: str
    content: str
    metadata: dict[str, Any] = {}


@app.middleware("http")
async def request_logger(request: Request, call_next):  # pragma: no cover - integration
    # Correlation/Request ID
    req_id = request.headers.get("x-request-id") or request.headers.get("X-Request-Id") or str(uuid4())
    client_ip = str(request.client.host if request.client else None)
    user_id = request.headers.get("x-user-id") or request.headers.get("X-User-Id")
    if user_id:
        bind_contextvars(request_id=req_id, client_ip=client_ip, user_id=user_id)
    else:
        bind_contextvars(request_id=req_id, client_ip=client_ip)
    logger.info("request_start", method=request.method, path=request.url.path)
    try:
        response = await call_next(request)
    finally:
        logger.info(
            "request_end",
            method=request.method,
            path=request.url.path,
            status_code=getattr(locals().get("response", None), "status_code", None),
        )
    if response is not None:
        response.headers["X-Request-ID"] = req_id
    clear_contextvars()
    return response


@app.get("/health")
async def health() -> dict[str, Any]:
    # DB connectivity check (best-effort)
    db_ok = True
    err: Optional[str] = None
    try:
        with get_session() as s:
            s.execute("SELECT 1")
    except Exception as e:  # pragma: no cover
        db_ok = False
        err = str(e)
    # Memory summary
    mem = MemoryManager()
    mem_summary = mem.summary()
    payload = {
        "status": "ok" if db_ok else "degraded",
        "database": db_ok,
        "error": err,
        "memory": mem_summary,
    }
    logger.info("health", **payload)
    return payload


@app.get("/status")
async def status() -> dict[str, Any]:
    settings = get_settings()
    env_validation = validate_environment()
    payload = {
        "environment": settings.server.ENVIRONMENT,
        "validation": env_validation,
    }
    logger.info("status", **payload)
    return payload


@app.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest, user=Depends(get_current_user)) -> QueryResponse:
    try:
        pipeline = GovernedAgentPipeline()
        # Metrics timer
        if LATENCY:
            with LATENCY.labels("/query").time():  # type: ignore[attr-defined]
                result = await pipeline.process_request(req.prompt)
        else:
            result = await pipeline.process_request(req.prompt)
        if REQS:
            REQS.labels("/query", "success").inc()  # type: ignore[attr-defined]
        # Correlation IDs into response metadata
        ctx = get_contextvars()
        req_id = ctx.get("request_id")
        md = dict(result.metadata or {})
        if req_id:
            md["request_id"] = req_id
        md["task_id"] = result.task_id
        if isinstance(user, dict) and user.get("user_id"):
            md["user_id"] = user.get("user_id")
        return QueryResponse(
            task_id=result.task_id,
            agent_role=result.agent_role,
            content=result.content,
            metadata=md,
        )
    except Exception as e:
        if REQS:
            REQS.labels("/query", "error").inc()  # type: ignore[attr-defined]
        logger.error("pipeline_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"pipeline_error: {e}")


if _settings.monitoring.METRICS_ENABLED and generate_latest:  # pragma: no cover
    @app.get("/metrics")
    async def metrics():
        data = generate_latest()  # type: ignore[operator]
        return Response(content=data, media_type=CONTENT_TYPE_LATEST)  # type: ignore[name-defined]


@app.get("/pipeline/summary")
async def pipeline_summary(user=Depends(get_current_user)) -> dict[str, Any]:
    """Return in-memory counts of stage successes/failures for quick debugging."""
    snap = PipelineStats.snapshot()
    logger.info("pipeline_summary", summary=snap)
    return {"summary": snap}


__all__ = ["app"]
