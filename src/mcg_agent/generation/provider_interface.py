from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple


class TextGenerationProvider(ABC):
    """Abstract provider for text generation operations.

    Implementations may call local MVLMs, hosted APIs, or stubs.
    All methods return (text, info) where info contains provider metadata.
    """

    @abstractmethod
    async def generate(self, prompt: str, **kwargs: Any) -> Tuple[str, Dict[str, Any]]:
        ...

    @abstractmethod
    async def revise(self, text: str, metadata: Dict[str, Any] | None = None) -> Tuple[str, Dict[str, Any]]:
        ...

    @abstractmethod
    async def summarize(self, text: str, metadata: Dict[str, Any] | None = None) -> Tuple[str, Dict[str, Any]]:
        ...


__all__ = ["TextGenerationProvider"]

