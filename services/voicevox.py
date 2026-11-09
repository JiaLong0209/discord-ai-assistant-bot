"""Async client for a VoiceVox Engine instance.

Uses two calls:
  1) POST /audio_query?speaker=ID (with text) to obtain a synthesis query JSON
  2) POST /synthesis?speaker=ID with that JSON to get WAV audio
"""

from __future__ import annotations

import asyncio
import io
import logging
from typing import Optional
from services.voice_config import VoiceVoxConfig  
from utils.text import extract_japanese_text

import aiohttp

import re

logger = logging.getLogger(__name__)

class VoiceVoxService:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:50021",
        default_speaker: int = 1,
        voicevox_config: VoiceVoxConfig = None,  
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.default_speaker = default_speaker
        self.voicevox_config = voicevox_config or VoiceVoxConfig()

    async def is_available(self) -> bool:
        """Check if the VoiceVox engine is currently reachable."""
        try:
            timeout = aiohttp.ClientTimeout(total=1.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{self.base_url}/version") as resp:
                    return resp.status == 200
        except Exception:
            return False

    async def synthesize(self, text: str, speaker: Optional[int] = None) -> Optional[bytes]:
        """Synthesize speech for the given text and return WAV bytes.
        
        Returns None if text contains no Japanese or VoiceVox engine is unreachable.
        """
        cleaned_text = extract_japanese_text(text)
        if not cleaned_text:
            return None

        speaker_id = speaker if speaker is not None else self.default_speaker
        try:
            timeout = aiohttp.ClientTimeout(total=5.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Step 1: audio_query
                params = {
                    "speaker": str(speaker_id),
                    "text": cleaned_text,
                }
                async with session.post(f"{self.base_url}/audio_query", params=params) as resp:
                    resp.raise_for_status()
                    query = await resp.json()

                # Apply config to query
                query = self.voicevox_config.apply_to_query(query)

                # Step 2: synthesis
                headers = {"Content-Type": "application/json"}
                async with session.post(
                    f"{self.base_url}/synthesis",
                    params={"speaker": str(speaker_id)},
                    headers=headers,
                    json=query,
                ) as resp2:
                    resp2.raise_for_status()
                    return await resp2.read()
        except (aiohttp.ClientError, asyncio.TimeoutError, ConnectionError, OSError) as err:
            logger.warning("VoiceVox is unavailable at %s: %s. Falling back to text-only.", self.base_url, err)
            return None
        except Exception as err:
            logger.warning("Unexpected error during VoiceVox synthesis: %s. Falling back to text-only.", err)
            return None
