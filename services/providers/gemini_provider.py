from __future__ import annotations

import asyncio
import logging
import re
from typing import Iterable, List, Optional, Tuple

import google.generativeai as genai

from .base import BaseAIProvider

logger = logging.getLogger(__name__)


class GeminiProvider(BaseAIProvider):
    """Google Gemini / Gemma provider implementation."""

    def __init__(
        self,
        api_key: str,
        model_text: str = "gemini-3.1-flash-lite",
        system_prompt: str | None = None
    ) -> None:
        genai.configure(api_key=api_key)
        self._model_text = model_text
        self._system_prompt = (system_prompt or "").strip()
        self._model = self._create_model(model_text)
        logger.info(f"GeminiProvider initialized with model={model_text}")

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model_text

    @model_name.setter
    def model_name(self, value: str) -> None:
        self._model_text = value
        self._model = self._create_model(value)
        logger.info(f"GeminiProvider model switched to {value}")

    # Backward compatibility with existing model_text property
    @property
    def model_text(self) -> str:
        return self.model_name

    @model_text.setter
    def model_text(self, value: str) -> None:
        self.model_name = value

    @property
    def system_prompt(self) -> str:
        return self._system_prompt

    @system_prompt.setter
    def system_prompt(self, value: str) -> None:
        self._system_prompt = (value or "").strip()
        self._model = self._create_model(self._model_text)
        logger.info("GeminiProvider system_prompt updated")

    def _create_model(self, model_name: str) -> genai.GenerativeModel:
        """Create a GenerativeModel instance with system_instruction if provided."""
        return genai.GenerativeModel(
            model_name=model_name,
            system_instruction=self._system_prompt if self._system_prompt else None
        )

    def _get_model(self, server_memory: Optional[str] = None) -> genai.GenerativeModel:
        """Get GenerativeModel with optional server memory combined into system instruction."""
        if not server_memory or not server_memory.strip():
            return self._model

        memory_block = (
            "\n\n【サーバーの記憶・コンテキスト（Server Memory）】\n"
            "以下はこのサーバーの永続的な記憶（メンバーの情報、過去の出来事、サーバーの知識）です。"
            "会話の中で自然に活用してください：\n"
            f"{server_memory.strip()}"
        )
        combined = f"{self._system_prompt}{memory_block}" if self._system_prompt else memory_block
        return genai.GenerativeModel(
            model_name=self._model_text,
            system_instruction=combined
        )

    @staticmethod
    def extract_clean_text(response) -> str:
        """Extract clean response text, filtering out thinking / reasoning scratchpads."""
        if not response:
            return ""

        parts = []
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", []) if content else []

        non_thought_parts = [p for p in parts if not getattr(p, "thought", False)]
        if non_thought_parts and len(non_thought_parts) < len(parts):
            text = "".join(getattr(p, "text", "") for p in non_thought_parts).strip()
        elif len(parts) > 1:
            text = getattr(parts[-1], "text", "").strip()
        else:
            text = (getattr(response, "text", "") or "").strip()

        # Remove explicit <thought> tags
        text = re.sub(r"<thought>.*?</thought>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()

        # Extract drafted final response if present
        draft_match = re.search(
            r"(?:Drafting final response|Final Response|Final Answer|Response):\s*\n*(.*)",
            text,
            flags=re.DOTALL | re.IGNORECASE
        )
        if draft_match and draft_match.group(1).strip():
            text = draft_match.group(1).strip()

        # Extract quotes if checklist scratchpad leaked
        if re.search(r"(?:•|\*|-)\s*(?:Character|Constraint Checklist|Confidence Score|Internal Monologue|Scenario):", text, flags=re.IGNORECASE):
            quotes = re.findall(r"(「[\s\S]*?」(?:\s*\n*\s*(?:翻譯|翻訳)?\s*[：:]?\s*「[\s\S]*?」)?)", text)
            if quotes:
                text = quotes[-1].strip()

        return text

    async def ask_text(
        self,
        prompt: str,
        context_messages: Optional[Iterable[str]] = None
    ) -> str:
        """Generate a response for a user prompt with optional context."""
        pieces = []
        if context_messages:
            pieces.extend(context_messages)
        pieces.append(prompt)
        full_prompt = "\n\n".join(pieces)

        logger.debug("ask_text() full_prompt=%r", full_prompt)
        response = await asyncio.to_thread(self._model.generate_content, full_prompt)
        self.log_response_info(response)
        return self.extract_clean_text(response) or "No response."

    def convert_history_to_gemini_format(self, history: List[dict]) -> list:
        """Convert chat history format to Gemini's expected format with strict alternating roles."""
        gemini_history = []
        for msg in history:
            role = "user" if msg["role"] == "user" else ("model" if msg["role"] in ("assistant", "model") else None)
            if not role:
                continue

            content = (msg.get("content") or "").strip()
            if not content:
                continue

            if gemini_history and gemini_history[-1]["role"] == role:
                gemini_history[-1]["parts"][0]["text"] += f"\n{content}"
            else:
                gemini_history.append({
                    "role": role,
                    "parts": [{"text": content}]
                })

        logger.debug("Converted history to gemini format: %s", gemini_history)
        return gemini_history

    async def ask_with_history(
        self,
        history: List[dict],
        user_message: str,
        server_memory: Optional[str] = None
    ) -> str:
        """Chat-style generation with rolling history and optional server memory."""
        clean_user = re.sub(r"^\[time:.*?\]\s*", "", user_message or "").strip()

        prompt_history = list(history) if history else []

        if clean_user:
            already_present = False
            if prompt_history and prompt_history[-1].get("role") == "user":
                last_clean = re.sub(r"^\[time:.*?\]\s*", "", prompt_history[-1].get("content", "")).strip()
                if last_clean == clean_user:
                    already_present = True

            if not already_present:
                prompt_history.append({"role": "user", "content": clean_user})

        gemini_history = self.convert_history_to_gemini_format(prompt_history)
        model = self._get_model(server_memory)
        response = await asyncio.to_thread(model.generate_content, gemini_history)
        self.log_response_info(response)
        return self.extract_clean_text(response) or "No response."

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
            {"text": text},
        ]
        logger.debug("describe_image() mime_type=%s text=%r", mime_type, text)
        response = await asyncio.to_thread(self._model.generate_content, parts)
        self.log_response_info(response)
        return self.extract_clean_text(response) or "No description."

    async def fix_grammar(self, text: str) -> str:
        """Return a grammar-corrected version of the input text."""
        prompt = (
            "You are a helpful editor. Rewrite the user's text with correct grammar, spelling, "
            "and natural phrasing. Preserve original meaning and tone, "
            "and tell me where there are grammar mistakes "
            "(Language can be Japanese, Chinese, and English).\n\n"
            f"Text: {text}"
        )
        logger.debug("fix_grammar() text=%r", text)
        model = genai.GenerativeModel(self._model_text)
        response = await asyncio.to_thread(model.generate_content, prompt)
        self.log_response_info(response)
        return self.extract_clean_text(response) or text

    async def compact_memory_text(
        self,
        current_memory: str,
        recent_history_text: str,
        guild_name: str = ""
    ) -> str:
        """Compact existing memory.md with recent chat history into a concise Markdown summary."""
        prompt = (
            "You are a memory consolidation assistant for an AI Discord bot.\n"
            "Your job is to update and compact the server's persistent Markdown memory file (memory.md).\n\n"
            f"=== CURRENT SERVER MEMORY ({guild_name}) ===\n"
            f"{current_memory.strip()}\n\n"
            f"=== RECENT CONVERSATIONS ===\n"
            f"{recent_history_text.strip()}\n\n"
            "=== INSTRUCTIONS ===\n"
            "1. Merge new information from recent conversations into the memory document.\n"
            "2. Keep it structured in clean Markdown with sections:\n"
            "   # Server Memory: <Guild Name>\n"
            "   ## Known Members (bullet points of user names, titles, topics, personality)\n"
            "   ## Server Facts & Lore (bullet points of server rules, inside jokes, facts)\n"
            "   ## Recent Highlights (short bullet summary of recent notable conversations or events)\n"
            "3. COMPACT & SUMMARIZE aggressively to save tokens: discard trivial chatter, keep facts concise.\n"
            "4. NEVER exceed 3,000 words. Keep it well under the token budget.\n"
            "5. Retain previously known valid member facts—do not wipe out past lore.\n"
            "6. Output ONLY the raw Markdown content. Do NOT include markdown code block wrappers (```markdown ... ```) or conversational commentary.\n"
        )
        model = genai.GenerativeModel(self._model_text)
        response = await asyncio.to_thread(model.generate_content, prompt)
        self.log_response_info(response)
        return self.extract_clean_text(response) or current_memory

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
        try:
            for model in genai.list_models():
                if "generateContent" not in model.supported_generation_methods:
                    continue

                model_id = model.name.split("/")[-1]

                if only_gemini and not (model_id.startswith("gemini") or model_id.startswith("gemma")):
                    continue

                if exclude_pro and "pro" in model_id.lower():
                    continue

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
        except Exception as exc:
            logger.warning("Failed to list models from Gemini API: %s. Using default fallback list.", exc)
            return [
                ("Gemini 2.5 Flash", "gemini-2.5-flash"),
                ("Gemini 2.0 Flash", "gemini-2.0-flash"),
                ("Gemini 1.5 Flash", "gemini-1.5-flash"),
            ]

