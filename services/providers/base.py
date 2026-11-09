from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Iterable


class BaseAIProvider(ABC):
    """Abstract Strategy interface for AI model providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider (e.g. 'gemini', 'openai', 'anthropic')."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Currently active model identifier."""
        ...

    @model_name.setter
    @abstractmethod
    def model_name(self, value: str) -> None:
        """Switch active model identifier."""
        ...

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """System prompt / persona for the model."""
        ...

    @system_prompt.setter
    @abstractmethod
    def system_prompt(self, value: str) -> None:
        """Update system prompt / persona."""
        ...

    @property
    def max_len(self) -> int:
        """Maximum response length (Discord limit is 2000)."""
        return 1900

    @abstractmethod
    async def ask_text(
        self,
        prompt: str,
        context_messages: Optional[Iterable[str]] = None
    ) -> str:
        """Generate a response for a single prompt with optional context."""
        ...

    @abstractmethod
    async def ask_with_history(
        self,
        history: List[dict],
        user_message: str,
        server_memory: Optional[str] = None
    ) -> str:
        """Chat-style generation with conversation history and optional server memory."""
        ...

    @abstractmethod
    async def describe_image(
        self,
        image_bytes: bytes,
        mime_type: str = "image/png",
        text: str = ""
    ) -> str:
        """Analyze an image and return description."""
        ...

    @abstractmethod
    async def fix_grammar(self, text: str) -> str:
        """Return grammar-corrected text."""
        ...

    @abstractmethod
    async def compact_memory_text(
        self,
        current_memory: str,
        recent_history_text: str,
        guild_name: str = ""
    ) -> str:
        """Compact existing memory.md with recent chat history into concise Markdown."""
        ...

    @abstractmethod
    def list_available_models(
        self,
        only_gemini: bool = False,
        exclude_pro: bool = True
    ) -> List[Tuple[str, str]]:
        """List available model labels and IDs."""
        ...

