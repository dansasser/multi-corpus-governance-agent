from __future__ import annotations

from typing import List
from pydantic import BaseModel, Field


class PunctuationPolicy(BaseModel):
    """Canonical punctuation/output control policy.

    Defaults are conservative; update from docs as needed.
    """

    allowed_sentence_terminators: List[str] = Field(default_factory=lambda: [".", "?", "!"])
    collapse_repeated_terminators: bool = True
    normalize_ellipsis: bool = True  # convert sequences of 3+ dots to "..."
    max_exclamations_per_100_words: int = 2
    enforce_space_after_punctuation: bool = True  # ensure a single space after .,?! when followed by a letter
    normalize_quotes: bool = True  # convert smart quotes to straight quotes by default


DEFAULT_PUNCTUATION_POLICY = PunctuationPolicy()


__all__ = ["PunctuationPolicy", "DEFAULT_PUNCTUATION_POLICY"]

