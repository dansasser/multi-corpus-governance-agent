from __future__ import annotations

from typing import Dict, List, Literal
from pydantic import BaseModel


class APICallLimits(BaseModel):
    limits: Dict[str, int] = {
        "ideator": 2,
        "drafter": 1,
        "critic": 2,
        "revisor": 1,  # fallback only when MVLM fails
        "summarizer": 0,  # emergency fallback only
    }


class CorpusAccessMatrix(BaseModel):
    # Access rules derived from governance + agents docs
    personal_allowed: List[str] = ["ideator", "critic"]
    social_allowed: List[str] = ["ideator", "drafter", "critic"]
    published_allowed: List[str] = ["ideator", "drafter", "critic"]

    def is_allowed(self, agent_role: str, corpus: Literal["personal", "social", "published"]) -> bool:
        role = agent_role.lower()
        if corpus == "personal":
            return role in self.personal_allowed
        if corpus == "social":
            return role in self.social_allowed
        if corpus == "published":
            return role in self.published_allowed
        return False


class RAGAccessPolicy(BaseModel):
    # Per docs: Critic always; Ideator conditionally for social/published (coverage gaps)
    rag_allowed: Dict[str, List[str]] = {
        "social": ["critic", "ideator"],
        "published": ["critic", "ideator"],
        "personal": [],
    }

    def is_rag_allowed(self, agent_role: str, corpus: str) -> bool:
        return agent_role.lower() in self.rag_allowed.get(corpus.lower(), [])


API_CALL_LIMITS = APICallLimits()
CORPUS_ACCESS = CorpusAccessMatrix()
RAG_POLICY = RAGAccessPolicy()


__all__ = [
    "APICallLimits",
    "CorpusAccessMatrix",
    "RAGAccessPolicy",
    "API_CALL_LIMITS",
    "CORPUS_ACCESS",
    "RAG_POLICY",
]

