"""Discord bot entrypoint with Cog-based architecture and Gemini integration.

This file initializes the bot, configures logging, loads environment settings,
registers cogs, and starts the bot. All secrets must be provided via env vars.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

import discord
from discord.ext import commands

from utils.config import get_settings
from services.gemini import GeminiService
from services.voicevox import VoiceVoxService


def configure_logging() -> None:
    """Configure application-wide logging format and level."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


intents = discord.Intents.default()
intents.message_content = True  # Required for some message-based features

# Use mention or a non-slash prefix for legacy text commands (we primarily use slash commands)
bot = commands.Bot(command_prefix=commands.when_mentioned_or("!"), intents=intents)


@bot.event
async def on_ready() -> None:
    logging.getLogger(__name__).info("Logged in as %s", bot.user)
    settings = getattr(bot, "_settings", None)
    USE_GUILD_SYNC = settings.use_guild_sync 
    DEV_GUILD_ID = settings.default_guild_id  


    try:
        if USE_GUILD_SYNC:
            # Sync commands to a specific guild (instant updates)
            in_guild = any(g.id == DEV_GUILD_ID for g in bot.guilds)
            if in_guild:

                guild_obj = discord.Object(id=DEV_GUILD_ID)
                # bot.tree.copy_global_to(guild=guild_obj)
                await bot.tree.sync(guild=guild_obj)

                # Clear old commands in that guild
                # bot.tree.clear_commands(guild=guild_obj)

                logging.getLogger(__name__).info(
                    "Slash commands synced instantly to test guild %s", DEV_GUILD_ID
                )
            else:
                logging.getLogger(__name__).warning(
                    "Test guild %s not found. Falling back to global sync.", DEV_GUILD_ID
                )
                await bot.tree.sync()
                logging.getLogger(__name__).info("Global slash commands synced (may take up to 1 hour)")
        else:
            # Global sync for all guilds (slower propagation)
            await bot.tree.sync()
            logging.getLogger(__name__).info("Global slash commands synced (may take up to 1 hour)")

    except Exception as sync_error:
        logging.getLogger(__name__).exception("Failed to sync app commands: %s", sync_error)

    current_cmds = await bot.tree.fetch_commands()

    print("All commands:")
    for cmd in current_cmds:
        print(f"\t{cmd}")


async def load_extensions() -> None:
    """Load all cogs from the cogs directory."""
    logger = logging.getLogger(__name__)
    for filename in os.listdir("./cogs"):
        # Only load regular Python files, skip dunders/hidden and package __init__
        if not filename.endswith(".py"):
            continue
        if filename.startswith("_"):
            continue
        ext_name = f"cogs.{filename[:-3]}"
        try:
            await bot.load_extension(ext_name)
            logger.info("Loaded extension: %s", ext_name)
        except Exception as exc:
            logger.exception("Failed to load extension %s: %s", ext_name, exc)


async def main() -> None:
    configure_logging()
    settings = get_settings()

    # Configure shared services and attach to bot for cogs to access.
    gemini_service = GeminiService(
        api_key=settings.google_api_key,
        model_text=settings.gemini_model or "gemini-2.0-flash",
        system_prompt=(
            settings.system_prompt 
        ),
    )
    setattr(bot, "gemini_service", gemini_service)
    voicevox_service = VoiceVoxService(
        base_url=settings.voicevox_host,
        default_speaker=settings.voicevox_speaker,
        voicevox_config=settings.voicevox_config
    )
    setattr(bot, "voicevox_service", voicevox_service)
    setattr(bot, "_settings", settings)

    async with bot:
        await load_extensions()
        await bot.start(settings.discord_bot_token)


if __name__ == "__main__":
    asyncio.run(main())




