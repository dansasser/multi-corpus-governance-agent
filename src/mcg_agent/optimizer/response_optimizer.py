from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

# Optional Prometheus metrics
try:  # pragma: no cover
    from prometheus_client import Counter, Histogram
except Exception:  # pragma: no cover
    Counter = None  # type: ignore
    Histogram = None  # type: ignore

from mcg_agent.mvlm.provider import MVLMProvider
from mcg_agent.utils.logging import get_logger
from mcg_agent.config import get_settings
from mcg_agent.utils.memory_manager import MemoryManager
from mcg_agent.quality.validators import ToneStyleValidator


_REQS = (
    Counter(
        "mcg_optimizer_requests_total",
        "Optimizer operation calls",
        labelnames=("op", "strategy", "result"),
    )
    if Counter
    else None
)

_LAT = (
    Histogram(
        "mcg_optimizer_latency_seconds",
        "Optimizer latency by op and strategy",
        labelnames=("op", "strategy"),
        buckets=(0.02, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0),
)
if Histogram
else None
)

_PRESS = (
    Counter(
        "mcg_optimizer_pressure_activations_total",
        "Times optimizer applied pressure-mode adjustments",
    )
    if Counter
    else None
)


@dataclass
class OptimizerConfig:
    strategy: str = "balanced"  # speed|quality|balanced|adaptive
    timebox_ms: int = 1500
    enable_cache: bool = True
    cache_ttl_ms: int = 60_000


class _TTLCache:
    def __init__(self, ttl_ms: int = 60_000, max_items: int = 256) -> None:
        self.ttl_ms = ttl_ms
        self.max_items = max_items
        self._store: Dict[str, Tuple[float, Tuple[str, Dict[str, Any]]]] = {}

    def get(self, key: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        now = time.time() * 1000
        ent = self._store.get(key)
        if not ent:
            return None
        ts, val = ent
        if now - ts > self.ttl_ms:
            self._store.pop(key, None)
            return None
        return val

    def set(self, key: str, val: Tuple[str, Dict[str, Any]]) -> None:
        if len(self._store) >= self.max_items:
            # naive eviction: drop oldest
            oldest = sorted(self._store.items(), key=lambda kv: kv[1][0])[:1]
            for k, _ in oldest:
                self._store.pop(k, None)
        self._store[key] = (time.time() * 1000, val)


class ResponseOptimizer:
    """Provider-agnostic response optimizer for revise/summarize ops.

    Works with MVLMProvider facade (which may be OpenAI, MVLM, or punctuation fallback).
    Adds timeboxing, simple strategy selection, and a small TTL cache.
    """

    def __init__(self, config: Optional[OptimizerConfig] = None) -> None:
        self.settings = get_settings()
        self.logger = get_logger("optimizer")
        self.cfg = config or OptimizerConfig(
            strategy=getattr(self.settings.optimization, "STRATEGY", "balanced"),
            timebox_ms=int(getattr(self.settings.optimization, "TIMEBOX_MS", 1500)),
            enable_cache=bool(getattr(self.settings.optimization, "ENABLE_CACHE", True)),
            cache_ttl_ms=int(getattr(self.settings.optimization, "CACHE_TTL_MS", 60_000)),
        )
        self.provider = MVLMProvider()
        self._cache = _TTLCache(self.cfg.cache_ttl_ms)
        # QA validator thresholds from settings
        self.qa = ToneStyleValidator(
            min_tone=float(getattr(self.settings.optimization, "QA_MIN_TONE", 0.5)),
            min_style=float(getattr(self.settings.optimization, "QA_MIN_STYLE", 0.5)),
            min_overall=float(getattr(self.settings.optimization, "QA_MIN_OVERALL", 0.6)),
        )

    def _key(self, op: str, text: str, meta: Optional[Dict[str, Any]]) -> str:
        m = hashlib.sha256()
        m.update(op.encode())
        m.update(text.encode())
        if meta:
            m.update(repr(sorted(meta.items())).encode())
        return m.hexdigest()

    async def _timebox(self, coro, op: str) -> Tuple[str, Dict[str, Any]]:
        try:
            return await asyncio.wait_for(coro, timeout=max(0.1, self.cfg.timebox_ms / 1000))
        except asyncio.TimeoutError:
            self.logger.warning("optimizer_timeout", op=op, timebox_ms=self.cfg.timebox_ms)
            return "", {"optimizer": "timeout"}
        except Exception as e:
            self.logger.warning("optimizer_error", op=op, error=str(e))
            return "", {"optimizer": "error", "detail": str(e)}

    async def optimize_revise(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> Tuple[str, Dict[str, Any]]:
        op = "revise"
        base_strat = self.cfg.strategy
        # Soft-pressure: if memory high, force speed strategy and bypass cache
        pressure = MemoryManager().should_apply_pressure()
        strat = "speed" if pressure else base_strat
        key = self._key(op, text, metadata)
        if self.cfg.enable_cache and not pressure:
            cached = self._cache.get(key)
            if cached:
                if _REQS:
                    _REQS.labels(op, strat, "cache").inc()  # type: ignore[attr-defined]
                return cached
        t0 = time.perf_counter()
        if _LAT:
            ctx = _LAT.labels(op, strat).time()  # type: ignore[attr-defined]
        else:
            ctx = None
        try:
            # Simple strategies: all call provider once for now; hooks ready for future expansion
            result = await self._timebox(self.provider.revise(text, metadata), op)
        finally:
            if ctx:
                ctx.observe_duration()  # type: ignore[attr-defined]
        # Optional QA gating for quality strategy
        if strat == "quality" and result[0]:
            tone = (metadata or {}).get("expected_tone") or "professional"
            style = (metadata or {}).get("expected_style") or "concise"
            scores = self.qa.validate(result[0], tone, style)
            info = {**(result[1] or {}), "qa": {
                "tone": scores.tone_match,
                "style": scores.style_consistency,
                "overall": scores.overall,
                "passed": scores.overall >= scores.pass_threshold,
            }}
            enforce = bool(getattr(self.settings.optimization, "QA_ENFORCE", False))
            if enforce and scores.overall < scores.pass_threshold:
                # fallback to original text
                return text, {**info, "qa_enforced": True}
            result = (result[0], info)
        # Annotate with pressure info
        if pressure:
            if _PRESS:
                _PRESS.inc()  # type: ignore[attr-defined]
            result = (result[0], {**(result[1] or {}), "pressure_mode": True})
        if not result[0]:
            # On failure/timeout, return original text
            if _REQS:
                _REQS.labels(op, strat, "fallback").inc()  # type: ignore[attr-defined]
            return text, {"optimizer": "fallback", "original": True}
        if self.cfg.enable_cache and not pressure:
            self._cache.set(key, result)
        if _REQS:
            _REQS.labels(op, strat, "ok").inc()  # type: ignore[attr-defined]
        return result

    async def optimize_summarize(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> Tuple[str, Dict[str, Any]]:
        op = "summarize"
        base_strat = self.cfg.strategy
        pressure = MemoryManager().should_apply_pressure()
        strat = "speed" if pressure else base_strat
        key = self._key(op, text, metadata)
        if self.cfg.enable_cache and not pressure:
            cached = self._cache.get(key)
            if cached:
                if _REQS:
                    _REQS.labels(op, strat, "cache").inc()  # type: ignore[attr-defined]
                return cached
        if _LAT:
            ctx = _LAT.labels(op, strat).time()  # type: ignore[attr-defined]
        else:
            ctx = None
        try:
            result = await self._timebox(self.provider.summarize(text, metadata), op)
        finally:
            if ctx:
                ctx.observe_duration()  # type: ignore[attr-defined]
        if strat == "quality" and result[0]:
            tone = (metadata or {}).get("expected_tone") or "professional"
            style = (metadata or {}).get("expected_style") or "concise"
            scores = self.qa.validate(result[0], tone, style)
            info = {**(result[1] or {}), "qa": {
                "tone": scores.tone_match,
                "style": scores.style_consistency,
                "overall": scores.overall,
                "passed": scores.overall >= scores.pass_threshold,
            }}
            enforce = bool(getattr(self.settings.optimization, "QA_ENFORCE", False))
            if enforce and scores.overall < scores.pass_threshold:
                return text, {**info, "qa_enforced": True}
            result = (result[0], info)
        if pressure:
            if _PRESS:
                _PRESS.inc()  # type: ignore[attr-defined]
            result = (result[0], {**(result[1] or {}), "pressure_mode": True})
        if not result[0]:
            if _REQS:
                _REQS.labels(op, strat, "fallback").inc()  # type: ignore[attr-defined]
            return text, {"optimizer": "fallback", "original": True}
        if self.cfg.enable_cache and not pressure:
            self._cache.set(key, result)
        if _REQS:
            _REQS.labels(op, strat, "ok").inc()  # type: ignore[attr-defined]
        return result


__all__ = ["ResponseOptimizer", "OptimizerConfig"]
