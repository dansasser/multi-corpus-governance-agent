from __future__ import annotations

import os
from typing import Any, Dict, Tuple

from mcg_agent.utils.punctuation import enforce_punctuation
from mcg_agent.protocols.punctuation_protocol import DEFAULT_PUNCTUATION_POLICY


class MVLMProvider:
    """Pluggable MVLM provider.

    Modes:
    - punctuation_only (default): applies punctuation rules deterministically.
    - noop: returns input unchanged.
    - http: placeholder for HTTP endpoint (to be implemented when endpoint is ready).
    """

    def __init__(self, mode: str | None = None) -> None:
        self.mode = (mode or os.environ.get("MCG_MVLM_MODE", "punctuation_only")).lower()
        self.http_url = os.environ.get("MCG_MVLM_HTTP_URL")
        self.http_api_key = os.environ.get("MCG_MVLM_HTTP_API_KEY")

    async def revise(self, text: str, metadata: Dict[str, Any] | None = None) -> Tuple[str, Dict[str, Any]]:
        if self.mode == "noop":
            return text, {"mode": self.mode}
        if self.mode == "http":
            # To be implemented: call external MVLM endpoint with governance headers
            # Return text unchanged for now and flag mode
            return text, {"mode": self.mode, "note": "http mode not yet implemented"}
        # punctuation_only default
        new_text, rules = enforce_punctuation(text, DEFAULT_PUNCTUATION_POLICY)
        info = {"mode": self.mode, "rules": rules}
        return new_text, info

    async def summarize(self, text: str, metadata: Dict[str, Any] | None = None) -> Tuple[str, Dict[str, Any]]:
        # For now use same behavior as revise; in future, apply controlled compression
        return await self.revise(text, metadata)


__all__ = ["MVLMProvider"]

