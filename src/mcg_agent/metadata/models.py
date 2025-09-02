from __future__ import annotations

from typing import List, Literal
from pydantic import BaseModel


class InputSource(BaseModel):
    corpus: Literal["Personal", "Social", "Published"]
    snippet_id: str
    source_text: str
    timestamp: str  # ISO-8601 format


class Attribution(BaseModel):
    claim_id: str
    source: str
    timestamp: str  # ISO-8601 format


class ToneFlags(BaseModel):
    voice_match_score: float
    seo_keywords: List[str]
    safety_flags: List[str]


class ChangeLog(BaseModel):
    change_id: str
    original_text: str
    revised_text: str
    reason: str
    applied_by: Literal["Critic", "Revisor"]


class TokenStats(BaseModel):
    input_tokens: int
    output_tokens: int


class MetadataBundle(BaseModel):
    task_id: str
    role: str
    input_sources: List[InputSource]
    attribution: List[Attribution]
    tone_flags: ToneFlags
    change_log: List[ChangeLog]
    long_tail_keywords: List[str]
    token_stats: TokenStats
    trimmed_sections: List[str]
    final_output: str


__all__ = [
    "InputSource",
    "Attribution",
    "ToneFlags",
    "ChangeLog",
    "TokenStats",
    "MetadataBundle",
]

