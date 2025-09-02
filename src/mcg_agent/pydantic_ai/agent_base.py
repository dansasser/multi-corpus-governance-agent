from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel


AgentRole = Literal["ideator", "drafter", "critic", "revisor", "summarizer"]


class AgentInput(BaseModel):
    task_id: str
    agent_role: AgentRole
    content: str
    context_pack: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class AgentOutput(BaseModel):
    task_id: str
    agent_role: AgentRole
    content: str
    context_pack: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = {}


class GovernanceContext(BaseModel):
    task_id: str
    user_prompt: str
    classification: Literal["chat", "writing", "voice", "retrieval-only"]
    input_sources: List[Dict[str, Any]] = []


__all__ = [
    "AgentRole",
    "AgentInput",
    "AgentOutput",
    "GovernanceContext",
]

