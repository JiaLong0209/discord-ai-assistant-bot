"""Configuration utilities for the Discord bot.

Loads environment variables and exposes a simple, typed accessor for required
and optional settings. This module should be imported before using services
that depend on these environment variables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional
from services import voice_config
from services.voice_config import VoiceVoxConfig

from dotenv import load_dotenv


# Load variables from a local .env file if present.
load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Strongly-typed settings loaded from environment variables."""

    discord_bot_token: str
    google_api_key: str
    default_guild_id: Optional[int]
    use_guild_sync: Optional[bool]
    gemini_model: Optional[str]
    system_prompt: Optional[str]
    voicevox_host: str
    voicevox_speaker: int
    voicevox_config: VoiceVoxConfig
    latest_n_history: int = 10


def get_settings() -> Settings:
    """Return the settings loaded from process environment variables.

    Raises:
        RuntimeError: If any required variable is missing.
    """

    discord_bot_token = os.getenv("DISCORD_BOT_TOKEN")
    google_api_key = os.getenv("GOOGLE_API_KEY")

    if not discord_bot_token:
        raise RuntimeError(
            "DISCORD_BOT_TOKEN is not set. Configure it in your environment or .env file."
        )
    if not google_api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. Configure it in your environment or .env file."
        )

    guild_raw = os.getenv("GUILD_ID")
    default_guild_id = int(guild_raw) if guild_raw and guild_raw.isdigit() else None

    gemini_model = os.getenv("GEMINI_MODEL")
    # Read system prompt from sys_prompt.txt file
    try:
        with open("sys_prompt.txt", "r", encoding="utf-8") as f:
            system_prompt = f.read().strip()
    except Exception:
        system_prompt = None

    voicevox_host = os.getenv("VOICEVOX_HOST", "http://127.0.0.1:50021")
    speaker_raw = os.getenv("VOICEVOX_SPEAKER", "1")
    voicevox_config = VoiceVoxConfig.load("voicevox_config.json")


    try:
        voicevox_speaker = int(speaker_raw)
    except ValueError:
        voicevox_speaker = 1
    
    use_guild_sync = os.getenv("USE_GUILD_SYNC", "false").lower() == "true"
    latest_n_history = int(os.getenv("LATEST_N_HISTORY", "10"))

    return Settings(
        discord_bot_token=discord_bot_token,
        google_api_key=google_api_key,
        default_guild_id=default_guild_id,
        use_guild_sync = use_guild_sync,
        gemini_model=gemini_model,
        system_prompt=system_prompt,
        voicevox_host=voicevox_host,
        voicevox_speaker=voicevox_speaker,
        voicevox_config = voicevox_config,
        latest_n_history=latest_n_history,
    )

