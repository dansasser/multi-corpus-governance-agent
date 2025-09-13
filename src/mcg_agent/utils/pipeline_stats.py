from __future__ import annotations

import threading
from typing import Dict


class PipelineStats:
    _lock = threading.RLock()
    _stage_counts: Dict[str, Dict[str, int]] = {
        "ideator": {"success": 0, "fail": 0},
        "drafter": {"success": 0, "fail": 0},
        "critic": {"success": 0, "fail": 0},
        "revisor": {"success": 0, "fail": 0},
        "summarizer": {"success": 0, "fail": 0},
    }

    @classmethod
    def inc(cls, stage: str, result: str) -> None:
        with cls._lock:
            if stage not in cls._stage_counts:
                cls._stage_counts[stage] = {"success": 0, "fail": 0}
            cls._stage_counts[stage][result] = cls._stage_counts[stage].get(result, 0) + 1

    @classmethod
    def snapshot(cls) -> Dict[str, Dict[str, int]]:
        with cls._lock:
            # return a shallow copy to avoid mutation issues
            return {k: dict(v) for k, v in cls._stage_counts.items()}


__all__ = ["PipelineStats"]

