from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, TypeVar, Awaitable, TYPE_CHECKING

if TYPE_CHECKING:  # avoid runtime import requirement
    from pydantic_ai import RunContext  # pragma: no cover
else:
    RunContext = Any  # type: ignore

from mcg_agent.pydantic_ai.agent_base import AgentInput
from mcg_agent.pydantic_ai.governance_validation import GovernanceRules
from mcg_agent.governance.api_limits import APICallGovernance
from mcg_agent.utils.audit import AuditLogger
from mcg_agent.utils.exceptions import (
    GovernanceViolationError,
    UnauthorizedCorpusAccessError,
)


F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


class SecureAgentTool:
    """Governance-enforced tool decorator for PydanticAI agents.

    Implements the exact governance pattern from docs/security/protocols/governance-protocol.md.
    """

    @staticmethod
    def governance_tool(
        required_permissions: List[str],
        corpus_access: Optional[List[str]] = None,
        max_calls_per_task: int = 0,
    ) -> Callable[[F], F]:
        def decorator(func: F) -> F:
            async def wrapper(ctx: RunContext[AgentInput], *args: Any, **kwargs: Any):
                # 1) Validate agent permissions
                await GovernanceRules.validate_agent_permissions(
                    agent_name=ctx.deps.agent_role,  # type: ignore[attr-defined]
                    required_permissions=required_permissions,
                    task_id=ctx.deps.task_id,  # type: ignore[attr-defined]
                )

                # 2) Validate corpus access if specified
                if corpus_access:
                    for corpus in corpus_access:
                        if not GovernanceRules.validate_corpus_access(
                            ctx.deps.agent_role,  # type: ignore[attr-defined]
                            corpus,
                        ):
                            raise UnauthorizedCorpusAccessError(
                                ctx.deps.agent_role, corpus  # type: ignore[attr-defined]
                            )

                # 3) Validate API call limits
                if max_calls_per_task > 0:
                    await APICallGovernance.validate_api_call(
                        ctx.deps.agent_role,  # type: ignore[attr-defined]
                        ctx.deps.task_id,  # type: ignore[attr-defined]
                    )

                # 4) Execute with logging
                result = await func(ctx, *args, **kwargs)

                # 5) Log successful execution
                await AuditLogger.log_tool_execution(
                    agent_role=ctx.deps.agent_role,  # type: ignore[attr-defined]
                    tool_name=func.__name__,
                    task_id=ctx.deps.task_id,  # type: ignore[attr-defined]
                    input_params=kwargs,
                    success=True,
                )

                return result

            return wrapper  # type: ignore[return-value]

        return decorator


__all__ = ["SecureAgentTool"]
