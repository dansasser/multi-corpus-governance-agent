from __future__ import annotations

import re
from typing import Tuple, List

from mcg_agent.protocols.punctuation_protocol import PunctuationPolicy, DEFAULT_PUNCTUATION_POLICY


SMART_QUOTES = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201C": '"',
    "\u201D": '"',
}


def enforce_punctuation(text: str, policy: PunctuationPolicy | None = None) -> Tuple[str, List[str]]:
    """Apply deterministic punctuation normalization per policy.

    Returns the normalized text and a list of applied rule IDs.
    """
    policy = policy or DEFAULT_PUNCTUATION_POLICY
    applied: List[str] = []
    out = text

    # Normalize smart quotes
    if policy.normalize_quotes:
        before = out
        for s, r in SMART_QUOTES.items():
            out = out.replace(s, r)
        if out != before:
            applied.append("normalize_quotes")

    # Normalize ellipsis: unicode … or 3+ dots -> "..."
    if policy.normalize_ellipsis:
        before = out
        out = out.replace("\u2026", "...")
        out = re.sub(r"\.{3,}", "...", out)
        if out != before:
            applied.append("normalize_ellipsis")

    # Collapse repeated terminators: e.g., !!! -> !, ?? -> ?, !?!! -> !?
    if policy.collapse_repeated_terminators:
        # Collapse runs of '!' and '?' to single, but keep combined '!?' or '?!'
        out2 = re.sub(r"!{2,}", "!", out)
        out2 = re.sub(r"\?{2,}", "?", out2)
        # Collapse mixed runs to a max of two chars and canonicalize order to '!?' if both present
        out2 = re.sub(r"([!?])([!?]){2,}", r"\1\2", out2)
        # Reduce sequences like '?!?' to '?!'
        out2 = re.sub(r"\?!\?+|!\?\!+", "?!", out2)
        if out2 != out:
            out = out2
            applied.append("collapse_repeated_terminators")

    # Enforce single space after punctuation when followed by a letter
    if policy.enforce_space_after_punctuation:
        out2 = re.sub(r"([\.\!\?])(\S)", lambda m: m.group(1) + (" " if m.group(2).isalpha() else "") + m.group(2), out)
        if out2 != out:
            out = out2
        # Mark as enforced regardless to indicate policy checked
        applied.append("enforce_space_after_punctuation")

    # Max exclamations per 100 words (soft normalization: demote extras to '.')
    if policy.max_exclamations_per_100_words >= 0:
        words = max(1, len(re.findall(r"\b\w+\b", out)))
        allowed = max(0, policy.max_exclamations_per_100_words * (words // 100 + (1 if words % 100 else 0)))
        ex_positions = [m.start() for m in re.finditer(r"!", out)]
        if len(ex_positions) > allowed:
            to_demote = len(ex_positions) - allowed
            chars = list(out)
            for idx in reversed(ex_positions[allowed:]):
                chars[idx] = "."
            out = "".join(chars)
            applied.append("limit_exclamations")

    return out, applied


__all__ = ["enforce_punctuation"]
