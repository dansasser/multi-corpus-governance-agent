from __future__ import annotations

from typing import Any, Dict
from datetime import datetime


class SecurityLogger:
    """Minimal security logger stub.

    Replace with structured logging + sink (e.g., structlog) as needed.
    """

    @staticmethod
    async def log_governance_violation(**kwargs: Any) -> None:
        record: Dict[str, Any] = {"ts": datetime.utcnow().isoformat(), **kwargs}
        # Placeholder: print or route to structured log
        print({"governance_violation": record})


__all__ = ["SecurityLogger"]

