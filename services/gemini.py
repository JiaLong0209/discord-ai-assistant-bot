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

    def convert_history_to_gemini_format(self, history: List[dict], user_message: str) -> list:
        gemini_history = []
        for msg in history:
            # Map roles: "assistant" -> "model", ignore any others except "user"
            if msg["role"] == "user":
                role = "user"
            elif msg["role"] in ("assistant", "model"):
                role = "model"
            else:
                continue  # skip any other roles (like "system")
            gemini_history.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })
        print(f"\n\tgemini_history: {gemini_history}")
        return gemini_history


    async def ask_with_history(self, history: List[dict], user_message: str) -> str:
        """Chat-style generation with a rolling history.

        history: list of (role, content) where role is "user" or "model".
        user_message: the latest user message appended to the history.
        """
        prompt_history = []
        if self._system_prompt:
            # If there is history and the first message is from the user, prepend system prompt
            if history and history[0]["role"] == "user":
                first = history[0]
                prompt_history.append({
                    "role": "user",
                    "content": f"{self._system_prompt}\n{first['content']}"
                })
                prompt_history.extend(history[1:])
            else:
                # No user history, prepend to current user message
                prompt_history.append({
                    "role": "user",
                    "content": f"{self._system_prompt}\n{user_message}"
                })
                user_message = None  # Already included
        else:
            prompt_history.extend(history)

        # Add the latest user message if not already included
        if user_message is not None:
            prompt_history.append({"role": "user", "content": user_message})

        gemini_history = self.convert_history_to_gemini_format(prompt_history, user_message)
        response = await asyncio.to_thread(self._model.generate_content, gemini_history)
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


