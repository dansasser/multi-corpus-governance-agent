from __future__ import annotations

from typing import Any

from mcg_agent.utils.exceptions import GovernanceViolationError


class GovernanceValidator:
    """Runtime governance validation hooks for agent pipeline stages.

    Matches the interface referenced in the governance protocol examples.
    Implement strict checks as rules solidify (tone, coverage, RAG eligibility, etc.).
    """

    @staticmethod
    async def validate_stage_execution(agent_role: str, governance_context: Any) -> bool:
        # Placeholder: ensure role is expected and classification present
        if agent_role not in {"ideator", "drafter", "critic", "revisor", "summarizer"}:
            raise GovernanceViolationError(f"Unknown agent role: {agent_role}")
        if not getattr(governance_context, "classification", None):
            raise GovernanceViolationError("Missing classification in governance context")
        return True

    @staticmethod
    async def validate_stage_output(agent_role: str, output: Any, governance_context: Any) -> bool:
        # Placeholder: ensure output has minimal fields and no empty content
        content = getattr(output, "content", None) or (output.get("content") if isinstance(output, dict) else None)  # noqa: E501
        if not content or not str(content).strip():
            raise GovernanceViolationError(f"{agent_role} produced empty content")
        return True


__all__ = ["GovernanceValidator"]

