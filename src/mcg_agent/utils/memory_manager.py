from __future__ import annotations

from typing import Any, Dict, Optional

try:  # pragma: no cover
    import psutil
except Exception:  # pragma: no cover
    psutil = None  # type: ignore

from mcg_agent.config import get_settings
from mcg_agent.utils.logging import get_logger


class MemoryManager:
    """Lightweight memory monitor with soft-pressure signaling."""

    def __init__(self, warn_percent: int = 80, pressure_percent: int = 90) -> None:
        self.settings = get_settings()
        self.logger = get_logger("memory")
        self.warn = warn_percent
        self.pressure = pressure_percent

    def summary(self) -> Dict[str, Any]:
        if not psutil:  # pragma: no cover
            return {"available": None, "used_percent": None, "psutil": False}
        vm = psutil.virtual_memory()
        return {
            "total": vm.total,
            "available": vm.available,
            "used": vm.used,
            "used_percent": vm.percent,
            "warn_threshold": self.warn,
            "pressure_threshold": self.pressure,
        }

    def should_apply_pressure(self) -> bool:
        if not psutil:  # pragma: no cover
            return False
        return psutil.virtual_memory().percent >= self.pressure

    def health_state(self) -> str:
        if not psutil:  # pragma: no cover
            return "unknown"
        p = psutil.virtual_memory().percent
        if p >= self.pressure:
            return "critical"
        if p >= self.warn:
            return "warning"
        return "ok"


__all__ = ["MemoryManager"]

