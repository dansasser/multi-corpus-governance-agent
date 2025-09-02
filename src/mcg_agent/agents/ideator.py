from __future__ import annotations

from typing import Any

from mcg_agent.protocols.context_protocol import ContextPack, ContextSnippet
from mcg_agent.search.models import (
    PersonalSearchFilters,
    SocialSearchFilters,
    PublishedSearchFilters,
)
from mcg_agent.search.tools import personal_search, social_search, published_search


class _Deps:
    def __init__(self, task_id: str, agent_role: str) -> None:
        self.task_id = task_id
        self.agent_role = agent_role


class _Ctx:
    def __init__(self, task_id: str, agent_role: str) -> None:
        self.deps = _Deps(task_id=task_id, agent_role=agent_role)


async def run_ideator_local(user_prompt: str, task_id: str) -> ContextPack:
    """Production local-mode Ideator runner.

    Invokes registered PydanticAI tools (with governance enforcement) under
    the Ideator role to assemble a ContextPack deterministically without
    requiring an LLM call. This is the default production path when an LLM
    is not necessary for context assembly.
    """
    ctx = _Ctx(task_id=task_id, agent_role="ideator")

    p = await personal_search(ctx, user_prompt, PersonalSearchFilters(), 5)
    s = await social_search(ctx, user_prompt, SocialSearchFilters(), 5)
    pub = await published_search(ctx, user_prompt, PublishedSearchFilters(), 5)

    snippets: list[ContextSnippet] = []
    for sn in p.snippets:
        snippets.append(
            ContextSnippet(
                snippet=sn.snippet,
                source="Personal",
                date=sn.date,
                tags=sn.tags,
                voice_terms=sn.voice_terms,
                attribution=sn.attribution,
                notes=sn.notes,
            )
        )
    for sn in s.snippets:
        snippets.append(
            ContextSnippet(
                snippet=sn.snippet,
                source="Social",
                date=sn.date,
                tags=sn.tags,
                voice_terms=sn.voice_terms,
                attribution=sn.attribution,
                notes=sn.notes,
            )
        )
    for sn in pub.snippets:
        snippets.append(
            ContextSnippet(
                snippet=sn.snippet,
                source="Published",
                date=sn.date,
                tags=sn.tags,
                voice_terms=sn.voice_terms,
                attribution=sn.attribution,
                notes=sn.notes,
            )
        )

    return ContextPack(snippets=snippets)


__all__ = ["run_ideator_local"]
