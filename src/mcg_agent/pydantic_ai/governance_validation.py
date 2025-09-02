from __future__ import annotations

from typing import List

from mcg_agent.protocols.governance_protocol import CORPUS_ACCESS


class GovernanceRules:
    """Runtime governance validation hooks.

    Note: Logic should be extended to enforce rules from docs/security/protocols/governance-protocol.md.
    """

    @staticmethod
    async def validate_agent_permissions(
        agent_name: str, required_permissions: List[str], task_id: str
    ) -> bool:
        # Placeholder for permission model; default allow, audited elsewhere.
        return True

    @staticmethod
    def validate_corpus_access(agent_name: str, corpus: str) -> bool:
        # Delegate to protocol-driven access matrix for single source of truth
        return CORPUS_ACCESS.is_allowed(agent_name, corpus.lower())


__all__ = ["GovernanceRules"]
