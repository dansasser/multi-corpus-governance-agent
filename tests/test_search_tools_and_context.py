import pytest

from mcg_agent.routing.pipeline import GovernedAgentPipeline
from mcg_agent.search.connectors import query_personal, query_social, query_published
from mcg_agent.search.models import (
    PersonalSearchFilters,
    SocialSearchFilters,
    PublishedSearchFilters,
)


def test_connectors_return_structures():
    p = query_personal("hello", PersonalSearchFilters())
    s = query_social("hello", SocialSearchFilters())
    pub = query_published("hello", PublishedSearchFilters())
    assert isinstance(p.snippets, list)
    assert isinstance(s.snippets, list)
    assert isinstance(pub.snippets, list)


@pytest.mark.asyncio
async def test_pipeline_context_assembly_uses_connectors():
    pipeline = GovernedAgentPipeline()
    ctx = await pipeline.assemble_context("hello world")
    assert "snippets" in ctx
    # May be empty when DB is not initialized; just ensure structure exists
    assert isinstance(ctx["snippets"], list)
