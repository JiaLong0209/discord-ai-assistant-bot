"""Wrapper around Google Generative AI (Gemini) for text, image, and chat.

This module centralizes the Gemini client configuration and exposes a small
API used by the bot cogs. It supports:
  - text generation (/q)
  - image understanding (/imginfo)
  - grammar fix (/fg)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Iterable, Optional, List, Tuple

import google.generativeai as genai

logger = logging.getLogger(__name__)



class GeminiService:
    """High-level service for interacting with Google Gemini models."""

    def __init__(
        self,
        api_key: str,
        model_text: str = "gemini-2.0-flash",
        system_prompt: str | None = None
    ) -> None:
        # Configure API key
        genai.configure(api_key=api_key)
        self.model_text = model_text
        self.max_len = 1900
        self._model = genai.GenerativeModel(model_text)
        self._system_prompt = system_prompt or ""
        logger.info(f"GeminiService initialized with model={model_text}")

    async def ask_text(
        self,
        prompt: str,
        context_messages: Optional[Iterable[str]] = None
    ) -> str:
        """Generate a response for a user prompt with optional context."""

        pieces = []
        if self._system_prompt:
            pieces.append(self._system_prompt)
        if context_messages:
            pieces.extend(context_messages)
        pieces.append(prompt)
        full_prompt = "\n\n".join(pieces)

        logger.debug("ask_text() full_prompt=%r", full_prompt)

        response = await asyncio.to_thread(self._model.generate_content, full_prompt)
        self.log_response_info(response)
        return (getattr(response, "text", "") or "").strip() or "No response."

    def convert_history_to_gemini_format(
        self,
        history: List[dict],
        user_message: str
    ) -> list:
        """Convert our chat history format to Gemini's expected format."""
        gemini_history = []
        for msg in history:
            if msg["role"] == "user":
                role = "user"
            elif msg["role"] in ("assistant", "model"):
                role = "model"
            else:
                continue
            gemini_history.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })

        logger.debug("Converted history to gemini format: %s", gemini_history)
        return gemini_history

    async def ask_with_history(
        self,
        history: List[dict],
        user_message: str
    ) -> str:
        """Chat-style generation with rolling history."""
        prompt_history = []
        if self._system_prompt:
            if history and history[0]["role"] == "user":
                first = history[0]
                prompt_history.append({
                    "role": "user",
                    "content": f"{self._system_prompt}\n{first['content']}"
                })
                prompt_history.extend(history[1:])
            else:
                prompt_history.append({
                    "role": "user",
                    "content": f"{self._system_prompt}\n{user_message}"
                })
                user_message = None
        else:
            prompt_history.extend(history)

        if user_message is not None:
            prompt_history.append({"role": "user", "content": user_message})

        gemini_history = self.convert_history_to_gemini_format(prompt_history, user_message)
        response = await asyncio.to_thread(self._model.generate_content, gemini_history)
        self.log_response_info(response)
        return (getattr(response, "text", "") or "").strip() or "No response."

    async def describe_image(
        self,
        image_bytes: bytes,
        mime_type: str = "image/png",
        text: str = ""
    ) -> str:
        """Analyze an image and return a description."""
        text = text or "Describe this image in detail."
        parts = [
            {"mime_type": mime_type, "data": image_bytes},
            {"text": self._system_prompt + text},
        ]
        logger.debug("describe_image() mime_type=%s text=%r", mime_type, text)
        response = await asyncio.to_thread(self._model.generate_content, parts)
        self.log_response_info(response)
        return (getattr(response, "text", "") or "").strip() or "No description."

    async def fix_grammar(self, text: str) -> str:
        """Return a grammar-corrected version of the input text."""
        prompt = (
            f"System_prompt: {self._system_prompt}",
            "You are a helpful editor. Rewrite the user's text with correct grammar, spelling, "
            "and natural phrasing. Preserve original meaning and tone, "
            "and tell me where there are grammar mistakes "
            "(Language can be Japanese, Chinese, and English).\n\n"
            f"Text: {text}"
        )
        logger.debug("fix_grammar() text=%r", text)
        response = await asyncio.to_thread(self._model.generate_content, prompt)
        self.log_response_info(response)
        return (getattr(response, "text", "") or "").strip() or text

    def log_response_info(self, response) -> None:
        """Log token usage and safety feedback."""
        if hasattr(response, "usage_metadata"):
            logger.info(
                "Tokens used — prompt: %s, completion: %s, total: %s",
                response.usage_metadata.prompt_token_count,
                response.usage_metadata.candidates_token_count,
                response.usage_metadata.total_token_count
            )

        if hasattr(response, "prompt_feedback"):
            logger.debug("Safety rating: %s", response.prompt_feedback)

    @staticmethod
    def list_available_models(only_gemini: bool = False, exclude_pro: bool = True) -> List[Tuple[str, str]]:
        """Fetch available models from the Gemini API, optionally excluding 'pro' models."""
        models = []
        for model in genai.list_models():
            if "generateContent" not in model.supported_generation_methods:
                continue

            model_id = model.name.split("/")[-1]

            # フィルター条件
            if only_gemini and not (model_id.startswith("gemini") or model_id.startswith("gemma")):
                continue

            if exclude_pro and "pro" in model_id.lower():
                continue  # proを除外

            label = (
                model_id.replace("-", " ")
                .title()
                .replace("Gemini", "Gemini")
                .replace("Gemma", "Gemma")
            )
            models.append((label, model_id))

        models = models[::-1]
        logger.info("Available non-pro models: %s", models)
        return models[:25]
