import asyncio
import pytest

from mcg_agent.protocols.routing_protocol import PipelineOrder, REVISE_CALL_TEMPLATE
from mcg_agent.routing.pipeline import GovernedAgentPipeline


def test_pipeline_order_matches_docs():
    order = PipelineOrder().stages
    assert order == ["ideator", "drafter", "critic", "revisor", "summarizer"]


def test_revise_template_contains_required_phrases():
    assert "Produce an outline only" in REVISE_CALL_TEMPLATE
    assert "Revise the outline to fix ONLY these issues" in REVISE_CALL_TEMPLATE


@pytest.mark.asyncio
async def test_pipeline_runs_in_sequence():
    pipeline = GovernedAgentPipeline()
    result = await pipeline.process_request("Short prompt")
    assert result.agent_role == "summarizer"
    assert isinstance(result.content, str)

