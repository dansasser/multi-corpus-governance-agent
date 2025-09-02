from __future__ import annotations

import asyncio
import time
from typing import Any
from uuid import uuid4

from mcg_agent.protocols.routing_protocol import PipelineOrder
from mcg_agent.protocols.context_protocol import ContextPack, ContextSnippet
from mcg_agent.agents.ideator import run_ideator_local
from mcg_agent.pydantic_ai.agent_base import AgentInput, AgentOutput, GovernanceContext
from mcg_agent.security.governance_enforcer import GovernanceValidator
from mcg_agent.utils.punctuation import enforce_punctuation
from mcg_agent.protocols.punctuation_protocol import DEFAULT_PUNCTUATION_POLICY
from mcg_agent.mvlm.provider import MVLMProvider


class GovernedAgentPipeline:
    """Orchestrates the five-agent pipeline with strict routing order.

    This is a framework-agnostic skeleton that enforces the sequence only.
    Agent execution is represented abstractly; integration with PydanticAI
    agents will be added in later phases.
    """

    def __init__(self) -> None:
        self.order = PipelineOrder().stages

    async def classify_prompt(self, user_prompt: str) -> str:
        # Minimal stub; real classifier to be implemented per plan
        return "writing" if len(user_prompt) > 80 else "chat"

    async def assemble_context(self, user_prompt: str) -> dict[str, Any]:
        # Delegate to Ideator local-mode runner (PydanticAI tools under governance)
        pack = await run_ideator_local(user_prompt, task_id="routing-ctx")
        return pack.model_dump()

    async def execute_agent_stage(self, agent_role: str, input_data: AgentInput) -> AgentOutput:
        # Placeholder execution: echo content and attach role metadata
        await asyncio.sleep(0)  # allow context switch
        return AgentOutput(
            task_id=input_data.task_id,
            agent_role=agent_role,
            content=input_data.content,
            context_pack=input_data.context_pack,
            metadata=input_data.metadata or {},
        )

    async def process_request(self, user_prompt: str) -> AgentOutput:
        task_id = str(uuid4())
        classification = await self.classify_prompt(user_prompt)
        gctx = GovernanceContext(
            task_id=task_id, user_prompt=user_prompt, classification=classification
        )

        # Stage: Ideator
        await GovernanceValidator.validate_stage_execution("ideator", gctx)
        ideator_input = AgentInput(
            task_id=task_id,
            agent_role="ideator",
            content=user_prompt,
            context_pack=await self.assemble_context(user_prompt),
        )
        ideator_out = await self.execute_agent_stage("ideator", ideator_input)
        await GovernanceValidator.validate_stage_output("ideator", ideator_out, gctx)

        # Stage: Drafter
        await GovernanceValidator.validate_stage_execution("drafter", gctx)
        drafter_input = AgentInput(
            task_id=task_id,
            agent_role="drafter",
            content=ideator_out.content,
            context_pack=ideator_out.context_pack,
            metadata=ideator_out.metadata,
        )
        drafter_out = await self.execute_agent_stage("drafter", drafter_input)
        await GovernanceValidator.validate_stage_output("drafter", drafter_out, gctx)

        # Stage: Critic
        await GovernanceValidator.validate_stage_execution("critic", gctx)
        critic_input = AgentInput(
            task_id=task_id,
            agent_role="critic",
            content=drafter_out.content,
            context_pack=drafter_out.context_pack,
            metadata=drafter_out.metadata,
        )
        critic_out = await self.execute_agent_stage("critic", critic_input)
        await GovernanceValidator.validate_stage_output("critic", critic_out, gctx)

        # Stage: Revisor
        await GovernanceValidator.validate_stage_execution("revisor", gctx)
        revisor_input = AgentInput(
            task_id=task_id,
            agent_role="revisor",
            content=critic_out.content,
            context_pack=critic_out.context_pack,
            metadata=critic_out.metadata,
        )
        revisor_out = await self.execute_agent_stage("revisor", revisor_input)
        # MVLM revise + punctuation enforcement at Revisor stage
        mvlm = MVLMProvider()
        rev_text, rev_info = await mvlm.revise(revisor_out.content, revisor_out.metadata)
        norm_text, rules = enforce_punctuation(rev_text, DEFAULT_PUNCTUATION_POLICY)
        if norm_text != revisor_out.content:
            # Log change in metadata change_log (applied_by Revisor)
            md = dict(revisor_out.metadata or {})
            change_log = list(md.get("change_log", []))
            change_log.append(
                {
                    "change_id": f"punct-{int(time.time())}",
                    "original_text": revisor_out.content,
                    "revised_text": norm_text,
                    "reason": "punctuation_normalization",
                    "applied_by": "Revisor",
                    "rules": rules,
                    "mvlm": rev_info,
                }
            )
            md["change_log"] = change_log
            revisor_out.content = norm_text
            revisor_out.metadata = md
        await GovernanceValidator.validate_stage_output("revisor", revisor_out, gctx)

        # Stage: Summarizer
        await GovernanceValidator.validate_stage_execution("summarizer", gctx)
        summarizer_input = AgentInput(
            task_id=task_id,
            agent_role="summarizer",
            content=revisor_out.content,
            context_pack=revisor_out.context_pack,
            metadata=revisor_out.metadata,
        )
        final_out = await self.execute_agent_stage("summarizer", summarizer_input)
        # MVLM summarize + punctuation enforcement at Summarizer
        sum_text, sum_info = await mvlm.summarize(final_out.content, final_out.metadata)
        norm_text, rules = enforce_punctuation(sum_text, DEFAULT_PUNCTUATION_POLICY)
        if norm_text != final_out.content:
            md = dict(final_out.metadata or {})
            md["punctuation_normalization"] = {"applied": True, "rules": rules, "mvlm": sum_info}
            final_out.content = norm_text
            final_out.metadata = md
        await GovernanceValidator.validate_stage_output("summarizer", final_out, gctx)

        return final_out


__all__ = ["GovernedAgentPipeline"]
