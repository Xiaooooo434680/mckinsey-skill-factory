from __future__ import annotations

from typing import Protocol


class LLMClient(Protocol):
    """Provider-neutral interface for optional model-assisted stages."""

    def complete(self, *, system: str, user: str) -> str:
        ...


class DisabledLLMClient:
    """Default client. It makes accidental network calls impossible."""

    def complete(self, *, system: str, user: str) -> str:
        raise RuntimeError("LLM provider is disabled; inject an LLMClient explicitly")
