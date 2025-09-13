from __future__ import annotations

import os
from typing import Any, Dict, Tuple

from mcg_agent.config import get_settings
from mcg_agent.utils.punctuation import enforce_punctuation
from mcg_agent.protocols.punctuation_protocol import DEFAULT_PUNCTUATION_POLICY
from mcg_agent.generation.provider_interface import TextGenerationProvider


class _PunctuationOnlyProvider(TextGenerationProvider):
    def __init__(self) -> None:
        self.mode = "punctuation_only"

    async def generate(self, prompt: str, **kwargs: Any) -> Tuple[str, Dict[str, Any]]:  # pragma: no cover
        # Deterministic: no-op, but normalize punctuation in prompt as a demonstration
        out, rules = enforce_punctuation(prompt, DEFAULT_PUNCTUATION_POLICY)
        return out, {"mode": self.mode, "rules": rules, "op": "generate"}

    async def revise(self, text: str, metadata: Dict[str, Any] | None = None) -> Tuple[str, Dict[str, Any]]:
        out, rules = enforce_punctuation(text, DEFAULT_PUNCTUATION_POLICY)
        return out, {"mode": self.mode, "rules": rules, "op": "revise"}

    async def summarize(self, text: str, metadata: Dict[str, Any] | None = None) -> Tuple[str, Dict[str, Any]]:
        # For parity, apply same normalization
        out, rules = enforce_punctuation(text, DEFAULT_PUNCTUATION_POLICY)
        return out, {"mode": self.mode, "rules": rules, "op": "summarize"}


def _build_provider() -> TextGenerationProvider:
    settings = get_settings()
    mode = (os.environ.get("GEN_PROVIDER") or getattr(settings, "GEN_PROVIDER", "punctuation_only")).lower()
    if mode == "openai":  # dev mode: calls OpenAI API
        try:
            from mcg_agent.generation.openai_provider import OpenAIProvider

            return OpenAIProvider()
        except Exception:  # pragma: no cover - dependency/env may be missing in some setups
            return _PunctuationOnlyProvider()
    # Future: if mode == "mvlm", hook to local MVLM manager/provider
    # Default: punctuation_only or unknown mode
    return _PunctuationOnlyProvider()


class MVLMProvider:
    """Unified provider facade used by the pipeline.

    Selects an underlying generation provider based on settings/env:
    - GEN_PROVIDER=openai → OpenAIProvider (dev)
    - GEN_PROVIDER=mvlm   → (reserved for MVLM hookup)
    - otherwise           → punctuation_only deterministic fallback
    """

    def __init__(self, mode: str | None = None) -> None:
        # Maintain backwards-compatible ctor signature; `mode` ignored now
        self._provider = _build_provider()

    async def revise(self, text: str, metadata: Dict[str, Any] | None = None) -> Tuple[str, Dict[str, Any]]:
        return await self._provider.revise(text, metadata)

    async def summarize(self, text: str, metadata: Dict[str, Any] | None = None) -> Tuple[str, Dict[str, Any]]:
        return await self._provider.summarize(text, metadata)


__all__ = ["MVLMProvider"]
