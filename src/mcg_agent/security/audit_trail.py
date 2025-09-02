from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List


@dataclass(frozen=True)
class AuditEvent:
    ts: str
    kind: str
    data: Dict[str, Any]


class ImmutableAuditTrail:
    """Append-only audit trail stub.

    For production, route to an append-only store (e.g., WORM storage,
    external log sink). This in-memory version maintains immutability by
    not exposing mutation of stored events.
    """

    def __init__(self) -> None:
        self._events: List[AuditEvent] = []

    def events(self) -> List[AuditEvent]:
        return list(self._events)

    async def log_event(self, kind: str, data: Dict[str, Any]) -> None:
        evt = AuditEvent(ts=datetime.utcnow().isoformat(), kind=kind, data=data)
        self._events.append(evt)
        print({"audit_trail": {"kind": kind, **data, "ts": evt.ts}})

    async def log_violation(self, data: Dict[str, Any]) -> None:
        await self.log_event("governance_violation", data)

    async def log_metadata_bundle(self, bundle: Dict[str, Any]) -> None:
        await self.log_event("metadata_bundle", bundle)


__all__ = ["ImmutableAuditTrail", "AuditEvent"]

