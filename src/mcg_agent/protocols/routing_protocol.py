from __future__ import annotations

from typing import List, Literal
from pydantic import BaseModel


ClassificationType = Literal["chat", "writing", "voice", "retrieval-only"]


class PipelineOrder(BaseModel):
    stages: List[str] = [
        "ideator",
        "drafter",
        "critic",
        "revisor",
        "summarizer",
    ]


REVISE_CALL_TEMPLATE = (
    "System: You are the Ideator. Produce an outline only. No prose.  \n"
    "Rules: Match this voice and style. Do not invent beyond context. Respect length.  \n"
    "Voice samples:  \n"
    "- {{published_sample_1}}  \n"
    "- {{social_sample_1}}  \n\n"
    "Context (attributed):  \n"
    "- {{snippet_1}} [Personal, 2024-11-02]  \n"
    "- {{snippet_2}} [Published, 2024-03-18]  \n\n"
    "User prompt: {{user_prompt}}  \n\n"
    "Current outline failed these checks:  \n"
    "- Tone: {{tone_issue}}  \n"
    "- Coverage: {{coverage_issue}}  \n\n"
    "Revise the outline to fix ONLY these issues. Keep all valid points.  \n"
    "Output: bullet outline, 5–7 bullets, 1 short headline."
)


__all__ = ["ClassificationType", "PipelineOrder", "REVISE_CALL_TEMPLATE"]

