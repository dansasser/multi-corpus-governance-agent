from __future__ import annotations

from typing import Any, Dict
from datetime import datetime


class AuditLogger:
    """Audit trail logger for tool executions and stage completions."""

    @staticmethod
    async def log_tool_execution(
        agent_role: str,
        tool_name: str,
        task_id: str,
        input_params: Dict[str, Any],
        success: bool,
    ) -> None:
        print(
            {
                "audit": {
                    "ts": datetime.utcnow().isoformat(),
                    "event": "tool_execution",
                    "agent_role": agent_role,
                    "tool_name": tool_name,
                    "task_id": task_id,
                    "success": success,
                }
            }
        )

    @staticmethod
    async def log_stage_completion(
        task_id: str,
        agent_role: str,
        execution_time: float,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        print(
            {
                "audit": {
                    "ts": datetime.utcnow().isoformat(),
                    "event": "stage_completion",
                    "task_id": task_id,
                    "agent_role": agent_role,
                    "execution_time": execution_time,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                }
            }
        )


__all__ = ["AuditLogger"]

