from __future__ import annotations

from typing import Optional, TYPE_CHECKING, Any

try:
    from pydantic_ai import tool
except Exception:  # pragma: no cover - test shim when lib unavailable
    def tool(name: str):  # type: ignore
        def deco(fn):
            return fn

        return deco

if TYPE_CHECKING:  # for type hints only; avoid runtime import requirements
    from pydantic_ai import RunContext  # pragma: no cover
else:
    RunContext = Any  # type: ignore

from mcg_agent.search.models import (
    PersonalSearchFilters,
    SocialSearchFilters,
    PublishedSearchFilters,
    PersonalSearchResult,
    SocialSearchResult,
    PublishedSearchResult,
)
from mcg_agent.search.connectors import (
    query_personal,
    query_social,
    query_published,
)
from mcg_agent.pydantic_ai.agent_base import AgentInput
from mcg_agent.pydantic_ai.secure_tools import SecureAgentTool


@tool("personal_search")
@SecureAgentTool.governance_tool(
    required_permissions=["corpus_query"],
    corpus_access=["personal"],
)
async def personal_search(
    ctx: RunContext,  # type: ignore[valid-type]
    query: str,
    filters: PersonalSearchFilters,
    limit: int = 20,
) -> PersonalSearchResult:
    return query_personal(query, filters, limit)


@tool("social_search")
@SecureAgentTool.governance_tool(
    required_permissions=["corpus_query"],
    corpus_access=["social"],
)
async def social_search(
    ctx: RunContext,  # type: ignore[valid-type]
    query: str,
    filters: SocialSearchFilters,
    limit: int = 30,
) -> SocialSearchResult:
    return query_social(query, filters, limit)


@tool("published_search")
@SecureAgentTool.governance_tool(
    required_permissions=["corpus_query"],
    corpus_access=["published"],
)
async def published_search(
    ctx: RunContext,  # type: ignore[valid-type]
    query: str,
    filters: PublishedSearchFilters,
    limit: int = 20,
) -> PublishedSearchResult:
    return query_published(query, filters, limit)


__all__ = ["personal_search", "social_search", "published_search"]
