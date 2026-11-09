"""Discord bot entrypoint with typed AIBot architecture, AI Provider Strategy, and Cog modularity.

This file initializes the bot, configures logging, loads environment settings,
registers modular cogs, and starts the bot.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

import discord
from discord.ext import commands

from utils.config import Settings, get_settings
from services.providers.factory import AIProviderFactory
from services.providers.base import BaseAIProvider
from services.voicevox import VoiceVoxService
from services.memory_service import MemoryService
from services.chat_history import ChatHistoryManager
from services.backup_service import BackupService
from services.ai_responder import AIResponder
from services.voice_playback import VoicePlaybackService


def configure_logging() -> None:
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler("logs/bot.log", encoding="utf-8"),
            logging.StreamHandler()
        ]
    )


class AIBot(commands.Bot):
    """Custom Discord Bot subclass with strongly-typed service dependencies."""

    def __init__(
        self,
        settings: Settings,
        ai_provider: BaseAIProvider,
        voicevox_service: Optional[VoiceVoxService] = None,
        memory_service: Optional[MemoryService] = None,
        backup_service: Optional[BackupService] = None,
        *args,
        **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self.settings = settings
        self.ai_provider = ai_provider
        self.voicevox_service = voicevox_service
        self.memory_service = memory_service
        self.backup_service = backup_service

        # Initialized in main() before extension loading
        self.ai_responder: Optional[AIResponder] = None
        self.playback_service: Optional[VoicePlaybackService] = None

        # Compatibility aliases for legacy cog access
        self._settings = settings
        self.gemini_service = ai_provider

    async def load_modular_extensions(self) -> None:
        """Load all decomposed modular cogs."""
        logger = logging.getLogger(__name__)
        extensions = [
            "cogs.chat_cog",
            "cogs.voice_cog",
            "cogs.voicevox_cog",
            "cogs.memory_cog",
            "cogs.settings_cog",
        ]
        for ext in extensions:
            try:
                await self.load_extension(ext)
                logger.info("Loaded extension: %s", ext)
            except Exception as exc:
                logger.exception("Failed to load extension %s: %s", ext, exc)


intents = discord.Intents.default()
intents.message_content = True


async def on_ready_handler(bot: AIBot) -> None:
    logger = logging.getLogger(__name__)
    logger.info("Logged in as %s", bot.user)
    settings = bot.settings
    USE_GUILD_SYNC = settings.use_guild_sync
    DEV_GUILD_ID = settings.default_guild_id

    try:
        if USE_GUILD_SYNC and DEV_GUILD_ID:
            in_guild = any(g.id == DEV_GUILD_ID for g in bot.guilds)
            if in_guild:
                guild_obj = discord.Object(id=DEV_GUILD_ID)
                await bot.tree.sync(guild=guild_obj)
                logger.info("Slash commands synced instantly to test guild %s", DEV_GUILD_ID)
            else:
                logger.warning("Test guild %s not found. Falling back to global sync.", DEV_GUILD_ID)
                await bot.tree.sync()
                logger.info("Global slash commands synced (may take up to 1 hour)")
        else:
            await bot.tree.sync()
            logger.info("Global slash commands synced (may take up to 1 hour)")
    except Exception as sync_error:
        logger.exception("Failed to sync app commands: %s", sync_error)

    current_cmds = await bot.tree.fetch_commands()
    print("All commands:")
    for cmd in current_cmds:
        print(f"\t{cmd}")


async def main() -> None:
    configure_logging()
    settings = get_settings()

    # 1. Instantiate AI Provider using Provider Factory (default: 'gemini')
    ai_provider = AIProviderFactory.create(
        "gemini",
        api_key=settings.google_api_key,
        model_text=settings.gemini_model or "gemini-3.1-flash-lite",
        system_prompt=settings.system_prompt,
    )

    # 2. Instantiate VoiceVox Service
    voicevox_service = VoiceVoxService(
        base_url=settings.voicevox_host,
        default_speaker=settings.voicevox_speaker,
        voicevox_config=settings.voicevox_config
    )

    # 3. Instantiate Domain Services
    memory_service = MemoryService(
        base_dir=settings.memory_dir,
        update_interval=settings.memory_update_interval
    )
    history_manager = ChatHistoryManager(latest_n=settings.latest_n_history)
    backup_service = BackupService(base_dir=settings.backup_dir)

    # 4. Construct Bot instance
    bot = AIBot(
        settings=settings,
        ai_provider=ai_provider,
        voicevox_service=voicevox_service,
        memory_service=memory_service,
        backup_service=backup_service,
        command_prefix="!",
        intents=intents
    )

    # 5. Wire Composite Services
    ai_responder = AIResponder(
        gemini=ai_provider,
        history_manager=history_manager,
        bot=bot,
        memory_service=memory_service
    )
    playback_service = VoicePlaybackService(
        bot=bot,
        voicevox_service=voicevox_service,
        backup_service=backup_service
    )

    bot.ai_responder = ai_responder
    bot.playback_service = playback_service

    @bot.event
    async def on_ready() -> None:
        await on_ready_handler(bot)

    @bot.command()
    async def reload(ctx: commands.Context, extension: str) -> None:
        await bot.reload_extension(f"cogs.{extension}")
        logging.info(f"ReLoaded {extension} done.")
        await ctx.send(f"ReLoaded {extension} done.", ephemeral=True)

    async with bot:
        await bot.load_modular_extensions()
        await bot.start(settings.discord_bot_token)


if __name__ == "__main__":
    asyncio.run(main())
