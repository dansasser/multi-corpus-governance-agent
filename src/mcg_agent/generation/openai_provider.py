from __future__ import annotations

import os
from typing import Any, Dict, Tuple

import httpx

from mcg_agent.generation.provider_interface import TextGenerationProvider
from mcg_agent.utils.logging import get_logger
from mcg_agent.config import get_settings


class OpenAIProvider(TextGenerationProvider):
    """Development provider that uses OpenAI's Chat Completions API via HTTP.

    Notes:
    - Requires OPENAI_API_KEY and OPENAI_MODEL in settings.
    - Designed for development; production may prefer an internal MVLM.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.logger = get_logger("openai_provider")
        self.api_key = self.settings.api.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY")
        self.model = os.environ.get("OPENAI_MODEL") or getattr(self.settings.api, "OPENAI_MODEL", None) or "gpt-4o-mini"
        self.base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.timeout_s = int(os.environ.get("OPENAI_TIMEOUT_S", "30"))

    async def _chat(self, system_prompt: str, user_prompt: str) -> str:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY not configured")
        url = f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,
        }
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()

    async def generate(self, prompt: str, **kwargs: Any) -> Tuple[str, Dict[str, Any]]:
        sys = "You are a helpful assistant. Keep responses concise and clear."
        out = await self._chat(sys, prompt)
        return out, {"provider": "openai", "model": self.model, "op": "generate"}

    async def revise(self, text: str, metadata: Dict[str, Any] | None = None) -> Tuple[str, Dict[str, Any]]:
        sys = "Revise the text for clarity and correctness. Do not change meaning."
        out = await self._chat(sys, text)
        return out, {"provider": "openai", "model": self.model, "op": "revise"}

    async def summarize(self, text: str, metadata: Dict[str, Any] | None = None) -> Tuple[str, Dict[str, Any]]:
        sys = "Summarize the text faithfully and concisely. Preserve key points."
        out = await self._chat(sys, text)
        return out, {"provider": "openai", "model": self.model, "op": "summarize"}


__all__ = ["OpenAIProvider"]

