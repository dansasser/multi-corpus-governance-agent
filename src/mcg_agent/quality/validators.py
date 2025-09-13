from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Any

# Deterministic tone/style validators used for basic Voice QA


TONE_KEYWORDS = {
    "professional": ["therefore", "furthermore", "however", "consequently", "moreover"],
    "casual": ["really", "pretty", "kind of", "sort of", "basically"],
    "formal": ["nevertheless", "accordingly", "subsequently", "notwithstanding"],
    "friendly": ["great", "awesome", "wonderful", "fantastic", "amazing"],
}


STYLE_CHARACTERISTICS = {
    "concise": {"max_avg_sentence_length": 20, "contractions_ok": True},
    "detailed": {"min_avg_sentence_length": 25, "contractions_ok": True},
    "conversational": {"contractions_ok": True, "informal_ok": True},
    "formal": {"contractions_ok": False, "informal_ok": False},
}


@dataclass
class QAScores:
    tone_match: float
    style_consistency: float
    overall: float
    pass_threshold: float
    tone_ok: bool
    style_ok: bool


class ToneStyleValidator:
    def __init__(self, min_tone: float = 0.5, min_style: float = 0.5, min_overall: float = 0.6) -> None:
        self.min_tone = min_tone
        self.min_style = min_style
        self.min_overall = min_overall

    def validate(self, text: str, expected_tone: str, expected_style: str) -> QAScores:
        tone_score = self._tone_score(text, expected_tone)
        style_score = self._style_score(text, expected_style)
        overall = 0.5 * tone_score + 0.5 * style_score
        tone_ok = tone_score >= self.min_tone
        style_ok = style_score >= self.min_style
        return QAScores(
            tone_match=tone_score,
            style_consistency=style_score,
            overall=overall,
            pass_threshold=self.min_overall,
            tone_ok=tone_ok,
            style_ok=style_ok,
        )

    def _tone_score(self, text: str, expected_tone: str) -> float:
        text_lower = text.lower()
        if expected_tone not in TONE_KEYWORDS:
            return 0.6
        kws = TONE_KEYWORDS[expected_tone]
        matches = sum(1 for kw in kws if kw in text_lower)
        return min(matches / max(1, len(kws)), 1.0)

    def _style_score(self, text: str, expected_style: str) -> float:
        chars = STYLE_CHARACTERISTICS.get(expected_style)
        if not chars:
            return 0.6
        # Sentence length
        sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
        avg_len = (sum(len(s.split()) for s in sentences) / len(sentences)) if sentences else 0
        score = 0.0
        checks = 0
        if "max_avg_sentence_length" in chars:
            score += 1.0 if avg_len <= chars["max_avg_sentence_length"] else 0.0
            checks += 1
        if "min_avg_sentence_length" in chars:
            score += 1.0 if avg_len >= chars["min_avg_sentence_length"] else 0.0
            checks += 1
        if "contractions_ok" in chars:
            contractions = ["don't", "won't", "can't", "isn't", "aren't", "wasn't", "weren't"]
            has_contractions = any(c in text.lower() for c in contractions)
            ok = (has_contractions is True) if chars["contractions_ok"] else (has_contractions is False)
            score += 1.0 if ok else 0.0
            checks += 1
        return score / max(1, checks)


__all__ = ["ToneStyleValidator", "QAScores"]

