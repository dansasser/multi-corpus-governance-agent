from __future__ import annotations

from typing import Dict

from mcg_agent.governance.call_tracker import CallTracker
from mcg_agent.utils.security_logger import SecurityLogger
from mcg_agent.utils.exceptions import APICallLimitExceededError
from mcg_agent.protocols.governance_protocol import API_CALL_LIMITS


class APICallGovernance:
    """Agent API call limit enforcement.

    Mirrors the spec in docs/security/protocols/governance-protocol.md.
    """

    # Single source of truth for limits comes from protocols
    AGENT_LIMITS: Dict[str, int] = API_CALL_LIMITS.limits

    @staticmethod
    async def validate_api_call(agent_name: str, task_id: str) -> bool:
        current_calls = await CallTracker.get_call_count(agent_name, task_id)
        max_calls = APICallGovernance.AGENT_LIMITS.get(agent_name, 0)

        if current_calls >= max_calls:
            await SecurityLogger.log_governance_violation(
                violation_type="api_call_limit_exceeded",
                agent_name=agent_name,
                current_calls=current_calls,
                max_calls=max_calls,
                task_id=task_id,
            )
            raise APICallLimitExceededError(agent_name, max_calls, current_calls + 1)

        await CallTracker.increment(agent_name, task_id)
        return True


__all__ = ["APICallGovernance"]
