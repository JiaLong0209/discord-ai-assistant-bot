from __future__ import annotations

import logging
from typing import Dict, Type

from .base import BaseAIProvider
from .gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)


class AIProviderFactory:
    """Factory for registering and creating AI model providers (Strategy + Factory Pattern)."""

    _registry: Dict[str, Type[BaseAIProvider]] = {
        "gemini": GeminiProvider,
    }

    @classmethod
    def register(cls, name: str, provider_cls: Type[BaseAIProvider]) -> None:
        """Register a new AI provider class."""
        key = name.strip().lower()
        cls._registry[key] = provider_cls
        logger.info("Registered AI provider: %s (%s)", key, provider_cls.__name__)

    @classmethod
    def create(cls, provider_name: str = "gemini", **kwargs) -> BaseAIProvider:
        """Instantiate an AI provider by name. Defaults to 'gemini'."""
        key = (provider_name or "gemini").strip().lower()
        provider_cls = cls._registry.get(key)
        if not provider_cls:
            available = list(cls._registry.keys())
            raise ValueError(f"Unknown AI provider '{provider_name}'. Available providers: {available}")
        return provider_cls(**kwargs)

    @classmethod
    def list_providers(cls) -> list[str]:
        """Return all registered provider names."""
        return list(cls._registry.keys())

