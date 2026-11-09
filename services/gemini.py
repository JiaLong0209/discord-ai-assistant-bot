"""Wrapper around Google Generative AI (Gemini) for text, image, and chat.

This module re-exports GeminiProvider as GeminiService to maintain backward
compatibility with existing codebase and tests while adhering to the BaseAIProvider
interface.
"""

from __future__ import annotations

from services.providers.gemini_provider import GeminiProvider

# Backward-compatible alias
GeminiService = GeminiProvider

__all__ = ["GeminiProvider", "GeminiService"]
