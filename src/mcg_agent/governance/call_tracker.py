from __future__ import annotations

import asyncio
import os
from typing import Dict, Tuple, Optional


class _MemoryCallTracker:
    _lock = asyncio.Lock()
    _calls: Dict[Tuple[str, str], int] = {}

    @classmethod
    async def get_call_count(cls, agent_name: str, task_id: str) -> int:
        async with cls._lock:
            return cls._calls.get((agent_name, task_id), 0)

    @classmethod
    async def increment(cls, agent_name: str, task_id: str) -> int:
        async with cls._lock:
            key = (agent_name, task_id)
            cls._calls[key] = cls._calls.get(key, 0) + 1
            return cls._calls[key]

    @classmethod
    async def reset_task(cls, task_id: str) -> None:
        async with cls._lock:
            keys = [k for k in cls._calls.keys() if k[1] == task_id]
            for k in keys:
                cls._calls.pop(k, None)


class _RedisCallTracker:
    def __init__(self) -> None:
        import redis  # lazy import to avoid dependency at import time

        host = os.environ.get("REDIS_HOST", "localhost")
        port = int(os.environ.get("REDIS_PORT", "6379"))
        password = os.environ.get("REDIS_PASSWORD")
        ssl = os.environ.get("REDIS_TLS", "false").lower() == "true"
        self._client = redis.Redis(host=host, port=port, password=password, ssl=ssl)

    def _key(self, agent_name: str, task_id: str) -> str:
        return f"mcg:calls:{task_id}:{agent_name}"

    async def get_call_count(self, agent_name: str, task_id: str) -> int:
        val = self._client.get(self._key(agent_name, task_id))
        return int(val) if val is not None else 0

    async def increment(self, agent_name: str, task_id: str) -> int:
        new_val = self._client.incr(self._key(agent_name, task_id))
        # Optional TTL per task key
        self._client.expire(self._key(agent_name, task_id), int(os.environ.get("MCG_CALL_TTL", "3600")))
        return int(new_val)

    async def reset_task(self, task_id: str) -> None:
        # Redis SCAN and DEL for task-specific keys
        cursor = 0
        pattern = f"mcg:calls:{task_id}:*"
        while True:
            cursor, keys = self._client.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                self._client.delete(*keys)
            if cursor == 0:
                break


def _get_backend() -> str:
    return os.environ.get("MCG_CALL_TRACKER_BACKEND", "memory").lower()


class CallTracker:
    """API call tracker with selectable backend.

    - memory (default): thread-safe in-memory counter for dev/tests.
    - redis: atomic counters with TTL using Redis (TLS/AUTH via env vars).
    """

    _memory = _MemoryCallTracker
    _redis: Optional[_RedisCallTracker] = None

    @classmethod
    def _impl(cls):
        if _get_backend() == "redis":
            if cls._redis is None:
                cls._redis = _RedisCallTracker()
            return cls._redis
        return cls._memory

    @classmethod
    async def get_call_count(cls, agent_name: str, task_id: str) -> int:
        return await cls._impl().get_call_count(agent_name, task_id)  # type: ignore[attr-defined]

    @classmethod
    async def increment(cls, agent_name: str, task_id: str) -> int:
        return await cls._impl().increment(agent_name, task_id)  # type: ignore[attr-defined]

    @classmethod
    async def reset_task(cls, task_id: str) -> None:
        return await cls._impl().reset_task(task_id)  # type: ignore[attr-defined]


__all__ = ["CallTracker"]
