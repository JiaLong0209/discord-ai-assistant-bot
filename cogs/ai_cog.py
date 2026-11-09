"""Backward-compatibility facade for AICog.

The monolithic AICog has been decomposed into modular, single-responsibility Cogs:
  - cogs/chat_cog.py: Text generation, image analysis, grammar fix, message listeners.
  - cogs/voice_cog.py: Voice channel join/exit, voice spoken replies.
  - cogs/voicevox_cog.py: VoiceVox TTS parameter configurations.
  - cogs/memory_cog.py: Server persistent memory (/memory group, /toggle_memory).
  - cogs/settings_cog.py: Gemini model, system prompt, history length, toggles, help.

This module is maintained as an adapter facade so existing tests and extensions
referencing AICog directly continue to work without breaking.
"""

from __future__ import annotations

import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from services.ai_responder import AIResponder
from services.backup_service import BackupService
from services.memory_service import MemoryService
from services.voice_playback import VoicePlaybackService
from utils.interaction_adapter import InteractionAdapter

logger = logging.getLogger(__name__)


class AICog(commands.Cog):
    """Backward-compatible facade Cog uniting modular AI bot capabilities."""

    def __init__(
        self,
        bot: commands.Bot,
        responder: AIResponder,
        backup_service: BackupService,
        memory_service: Optional[MemoryService] = None,
        playback_service: Optional[VoicePlaybackService] = None
    ) -> None:
        self.bot = bot
        self.responder = responder
        self.backup_service = backup_service
        self.memory_service = memory_service
        self.playback_service = playback_service or VoicePlaybackService(
            bot=bot,
            voicevox_service=getattr(bot, "voicevox_service", None),
            backup_service=backup_service
        )

        # Settings
        self.listen_all_messages = False
        self.mention_user = True
        self.backup_audio = True
        self.backup_text = True
        self.use_server_memory = True

    def _make_fake_interaction(self, message: discord.Message) -> InteractionAdapter:
        return InteractionAdapter.from_message(message)

    async def send_tts_response(
        self,
        interaction: discord.Interaction,
        answer: str,
        attach_audio_file: bool = True,
        mention_user: bool = True
    ) -> None:
        await self.playback_service.play_or_reply(
            interaction=interaction,
            answer=answer,
            attach_audio_file=attach_audio_file,
            mention_user=mention_user
        )

    @app_commands.command(name="toggle_memory", description="Toggle whether AI uses persistent server memory (memory.md).")
    async def toggle_memory(self, interaction: discord.Interaction) -> None:
        self.use_server_memory = not self.use_server_memory
        if self.responder:
            self.responder.use_server_memory = self.use_server_memory
        status = "enabled" if self.use_server_memory else "disabled"
        await interaction.response.send_message(f"Server memory injection is now **{status}**.")


async def setup(bot: commands.Bot) -> None:
    """Load all decomposed modular cogs."""
    extensions = [
        "cogs.chat_cog",
        "cogs.voice_cog",
        "cogs.voicevox_cog",
        "cogs.memory_cog",
        "cogs.settings_cog",
    ]
    for ext in extensions:
        if ext not in bot.extensions:
            await bot.load_extension(ext)
