from __future__ import annotations

import json
import os
import threading
import time
from collections import OrderedDict
from typing import Any, Optional, Tuple

# Optional compression
try:  # pragma: no cover
    import zlib
except Exception:  # pragma: no cover
    zlib = None  # type: ignore

# Optional Prometheus metrics
try:  # pragma: no cover
    from prometheus_client import Counter, Gauge
except Exception:  # pragma: no cover
    Counter = None  # type: ignore
    Gauge = None  # type: ignore


def _extract_namespace(key: str) -> str:
    # Expected format: mcg:cache:{namespace}:<json>
    try:
        if key.startswith("mcg:cache:"):
            rest = key[len("mcg:cache:"):]
            ns = rest.split(":", 1)[0]
            return ns
    except Exception:
        pass
    return "default"


_HITS = (
    Counter("mcg_cache_hits_total", "Cache hits", labelnames=("namespace",)) if Counter else None
)
_MISSES = (
    Counter("mcg_cache_misses_total", "Cache misses", labelnames=("namespace",)) if Counter else None
)
_EVICTIONS = (
    Counter("mcg_cache_evictions_total", "Cache evictions", labelnames=("backend",)) if Counter else None
)
_ITEMS = Gauge("mcg_cache_items", "Cache items count", labelnames=("backend",)) if Gauge else None
_BYTES = Gauge("mcg_cache_bytes", "Cache memory bytes (approx)", labelnames=("backend",)) if Gauge else None


class _MemoryStore:
    def __init__(self, max_items: int = 1024, ttl_s: int = 90, compress: bool = False) -> None:
        self.max_items = max_items
        self.ttl_ms = max(1, ttl_s) * 1000
        self.compress = compress and zlib is not None
        self._lock = threading.RLock()
        # key -> (ts_ms, value_bytes or str)
        self._store: OrderedDict[str, Tuple[float, bytes | str]] = OrderedDict()
        self._bytes = 0
        self._start_cleaner()

    def _start_cleaner(self) -> None:
        def _run():
            while True:
                time.sleep(10)
                try:
                    self._cleanup_expired()
                except Exception:
                    pass

        t = threading.Thread(target=_run, daemon=True)
        t.start()

    def _cleanup_expired(self) -> None:
        now = time.time() * 1000
        with self._lock:
            to_del = []
            for k, (ts, _) in list(self._store.items()):
                if now - ts > self.ttl_ms:
                    to_del.append(k)
            for k in to_del:
                _, v = self._store.pop(k, (0, b""))
                self._bytes -= len(v) if isinstance(v, (bytes, bytearray)) else len(str(v).encode())
            if _ITEMS:
                _ITEMS.labels("memory").set(len(self._store))  # type: ignore[attr-defined]
            if _BYTES:
                _BYTES.labels("memory").set(self._bytes)  # type: ignore[attr-defined]

    def get(self, key: str) -> Optional[str]:
        now = time.time() * 1000
        with self._lock:
            ent = self._store.get(key)
            if not ent:
                return None
            ts, v = ent
            if now - ts > self.ttl_ms:
                # expired
                self._store.pop(key, None)
                self._bytes -= len(v) if isinstance(v, (bytes, bytearray)) else len(str(v).encode())
                return None
            # LRU: move to end
            self._store.move_to_end(key)
            if isinstance(v, (bytes, bytearray)):
                try:
                    data = zlib.decompress(v).decode("utf-8") if self.compress and zlib else v.decode("utf-8")
                except Exception:
                    data = ""
                return data
            return str(v)

    def set(self, key: str, value: str, ttl_s: Optional[int] = None) -> None:
        payload: bytes | str
        if self.compress and zlib:
            payload = zlib.compress(value.encode("utf-8"))
        else:
            payload = value
        with self._lock:
            # Evict if capacity
            if len(self._store) >= self.max_items:
                k, (ts_old, v_old) = self._store.popitem(last=False)
                self._bytes -= len(v_old) if isinstance(v_old, (bytes, bytearray)) else len(str(v_old).encode())
                if _EVICTIONS:
                    _EVICTIONS.labels("memory").inc()  # type: ignore[attr-defined]
            self._store[key] = (time.time() * 1000 if ttl_s is None else time.time() * 1000, payload)
            self._bytes += len(payload) if isinstance(payload, (bytes, bytearray)) else len(str(payload).encode())
            if _ITEMS:
                _ITEMS.labels("memory").set(len(self._store))  # type: ignore[attr-defined]
            if _BYTES:
                _BYTES.labels("memory").set(self._bytes)  # type: ignore[attr-defined]


class Cache:
    def __init__(self) -> None:
        self.backend = os.environ.get("MCG_CACHE_BACKEND", "none").lower()
        self.ttl = int(os.environ.get("MCG_CACHE_TTL", "90"))
        self._redis = None
        self._mem: Optional[_MemoryStore] = None
        self._compress = os.environ.get("MCG_CACHE_COMPRESS", "false").lower() == "true"
        self._mem_max_items = int(os.environ.get("MCG_CACHE_MAX_ITEMS", "1024"))
        if self.backend == "redis":
            import redis

            host = os.environ.get("REDIS_HOST", "localhost")
            port = int(os.environ.get("REDIS_PORT", "6379"))
            password = os.environ.get("REDIS_PASSWORD")
            ssl = os.environ.get("REDIS_TLS", "false").lower() == "true"
            self._redis = redis.Redis(host=host, port=port, password=password, ssl=ssl)
        elif self.backend == "memory":
            self._mem = _MemoryStore(max_items=self._mem_max_items, ttl_s=self.ttl, compress=self._compress)

    def get(self, key: str) -> Optional[str]:
        if self.backend == "redis" and self._redis is not None:
            val = self._redis.get(key)
            if val:
                if _HITS:
                    _HITS.labels(_extract_namespace(key)).inc()  # type: ignore[attr-defined]
                return val.decode("utf-8")
            if _MISSES:
                _MISSES.labels(_extract_namespace(key)).inc()  # type: ignore[attr-defined]
            return None
        if self.backend == "memory" and self._mem is not None:
            out = self._mem.get(key)
            if out is not None:
                if _HITS:
                    _HITS.labels(_extract_namespace(key)).inc()  # type: ignore[attr-defined]
                return out
            if _MISSES:
                _MISSES.labels(_extract_namespace(key)).inc()  # type: ignore[attr-defined]
            return None
        # none backend
        return None

    def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        if self.backend == "redis" and self._redis is not None:
            self._redis.setex(key, ttl or self.ttl, value)
            if _ITEMS:
                try:
                    size = int(self._redis.dbsize())  # type: ignore[attr-defined]
                    _ITEMS.labels("redis").set(size)
                except Exception:
                    pass
            return
        if self.backend == "memory" and self._mem is not None:
            self._mem.set(key, value, ttl)
            return
        # none backend: noop
        return

    @staticmethod
    def key(namespace: str, **kwargs: Any) -> str:
        return f"mcg:cache:{namespace}:" + json.dumps(kwargs, sort_keys=True)


__all__ = ["Cache"]
