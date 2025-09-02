from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel


class ContextSnippet(BaseModel):
    snippet: str
    source: Literal["Personal", "Social", "Published", "External"]
    date: str
    tags: List[str] = []
    voice_terms: List[str] = []
    attribution: str
    notes: str = ""


class ContextPack(BaseModel):
    snippets: List[ContextSnippet]
    coverage_score: Optional[float] = None
    tone_score: Optional[float] = None
    diversity_ok: Optional[bool] = None


__all__ = ["ContextSnippet", "ContextPack"]

