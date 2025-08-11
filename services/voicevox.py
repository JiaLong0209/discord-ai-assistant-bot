"""Async client for a VoiceVox Engine instance.

Uses two calls:
  1) POST /audio_query?speaker=ID (with text) to obtain a synthesis query JSON
  2) POST /synthesis?speaker=ID with that JSON to get WAV audio
"""

from __future__ import annotations

import io
from typing import Optional
from services.voice_config import VoiceVoxConfig  

import aiohttp


class VoiceVoxService:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:50021",
        default_speaker: int = 1,
        voicevox_config: VoiceVoxConfig = None,  
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.default_speaker = default_speaker
        self.voicevox_config = voicevox_config or VoiceVoxConfig()  # Use default if not provided

    async def synthesize(self, text: str, speaker: Optional[int] = None) -> bytes:
        """Synthesize speech for the given text and return WAV bytes."""
        speaker_id = speaker if speaker is not None else self.default_speaker
        async with aiohttp.ClientSession() as session:
            # Step 1: audio_query
            params = {
                "speaker": str(speaker_id),
                "text": text,
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
                audio_bytes = await resp2.read()
                return audio_bytes

