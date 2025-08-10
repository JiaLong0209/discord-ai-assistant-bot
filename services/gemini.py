"""Wrapper around Google Generative AI (Gemini) for text, image, and chat.

This module centralizes the Gemini client configuration and exposes a small
API used by the bot cogs. It supports:
  - text generation (/q)
  - image understanding (/imginfo)
  - grammar fix (/fg)
"""

from __future__ import annotations

from typing import Iterable, Optional, List, Tuple
import asyncio

import google.generativeai as genai


class GeminiService:
    """High-level service for interacting with Google Gemini models."""

    def __init__(self, api_key: str, model_text: str = "gemini-2.0-flash", system_prompt: str | None = None) -> None:
        # Configure the library with the provided API key.
        genai.configure(api_key=api_key)
        self.model_text = model_text
        self.max_len = 1800
        self._model = genai.GenerativeModel(model_text)
        # Optional system prompt to steer the model persona and output style
        self._system_prompt = system_prompt or ""

    async def ask_text(self, prompt: str, context_messages: Optional[Iterable[str]] = None) -> str:
        """Generate a response for a user prompt with optional context."""
        pieces = []
        if self._system_prompt:
            pieces.append(self._system_prompt)
        if context_messages:
            pieces.extend(context_messages)
        pieces.append(prompt)
        full_prompt = "\n\n".join(pieces)
        # google-generativeai provides synchronous generate_content; run off the event loop
        response = await asyncio.to_thread(self._model.generate_content, full_prompt)
        self.print_response_info(response)
        return (getattr(response, "text", "") or "").strip() or "No response."

    async def ask_with_history(
        self, messages: List[Tuple[str, str]], user_message: str
    ) -> str:
        """Chat-style generation with a rolling history.

        messages: list of (role, content) where role is "user" or "model".
        user_message: the latest user message appended to the history.
        """
        contents: List[dict] = []
        if self._system_prompt:
            contents.append({"text": self._system_prompt})
        for role, content in messages:
            contents.append({"text": content})
        contents.append({"text": user_message})
        response = await asyncio.to_thread(self._model.generate_content, contents)
        self.print_response_info(response)
        return (getattr(response, "text", "") or "").strip() or "No response."

    async def describe_image(self, image_bytes: bytes, mime_type: str = "image/png", text: str = "") -> str:
        """Analyze an image and return a description or analysis."""
        parts = [
            {
                "mime_type": mime_type,
                "data": image_bytes,
            },
            {"text": self._system_prompt + "Describe this image in detail." + text },
        ]
        response = await asyncio.to_thread(self._model.generate_content, parts)
        return (getattr(response, "text", "") or "").strip() or "No description."

    async def fix_grammar(self, text: str) -> str:
        """Return a grammar- and style-corrected version of the input text."""
        prompt = ( 
            f"System_prompt: {self._system_prompt}", 
            "You are a helpful editor. Rewrite the user's text with correct grammar, spelling, "
            "and natural phrasing. Preserve original meaning and tone, and tell me where are wrong grammar (Language can be Japanese, Chinese and English etc. \n\n"
            f"Text: {text}"
        )
        response = await asyncio.to_thread(self._model.generate_content, prompt)
        self.print_response_info(response)
        return (getattr(response, "text", "") or "").strip() or text

    def print_response_info(self, response) -> None:
        if hasattr(response, "usage_metadata"):
            print(f"Tokens used — prompt: {response.usage_metadata.prompt_token_count}, "
                f"completion: {response.usage_metadata.candidates_token_count}, "
                f"total: {response.usage_metadata.total_token_count}")

        if hasattr(response, "prompt_feedback"):
            print(f"Safety rating: {response.prompt_feedback}")


