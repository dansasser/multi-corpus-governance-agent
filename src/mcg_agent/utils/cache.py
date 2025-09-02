from __future__ import annotations

import json
import os
from typing import Any, Optional


class Cache:
    def __init__(self) -> None:
        self.backend = os.environ.get("MCG_CACHE_BACKEND", "none").lower()
        self.ttl = int(os.environ.get("MCG_CACHE_TTL", "90"))
        self._redis = None
        if self.backend == "redis":
            import redis

            host = os.environ.get("REDIS_HOST", "localhost")
            port = int(os.environ.get("REDIS_PORT", "6379"))
            password = os.environ.get("REDIS_PASSWORD")
            ssl = os.environ.get("REDIS_TLS", "false").lower() == "true"
            self._redis = redis.Redis(host=host, port=port, password=password, ssl=ssl)

    def get(self, key: str) -> Optional[str]:
        if self.backend == "redis" and self._redis is not None:
            val = self._redis.get(key)
            return val.decode("utf-8") if val else None
        return None

    def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        if self.backend == "redis" and self._redis is not None:
            self._redis.setex(key, ttl or self.ttl, value)

    @staticmethod
    def key(namespace: str, **kwargs: Any) -> str:
        return f"mcg:cache:{namespace}:" + json.dumps(kwargs, sort_keys=True)


__all__ = ["Cache"]

