from __future__ import annotations

import asyncio
import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from services.ai_responder import AIResponder
from services.voice_playback import VoicePlaybackService
from services.memory_service import MemoryService
from services.message_preprocessor import MessagePreprocessor
from utils.discord_context import GuildContext, require_service
from utils.interaction_adapter import InteractionAdapter

logger = logging.getLogger(__name__)


class ChatCog(commands.Cog, name="Chat"):
    """Cog for text Q&A, image analysis, grammar fix, and message listeners."""

    def __init__(
        self,
        bot: commands.Bot,
        responder: AIResponder,
        playback_service: VoicePlaybackService,
        memory_service: Optional[MemoryService] = None,
        listen_all_messages: bool = False,
        mention_user: bool = True
    ) -> None:
        self.bot = bot
        self.responder = responder
        self.playback_service = playback_service
        self.memory_service = memory_service
        self.listen_all_messages = listen_all_messages
        self.mention_user = mention_user

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        ctx = GuildContext.from_message(message)
        user_name = message.author.display_name

        question = MessagePreprocessor.normalize(message=message)
        self.responder._log_interaction(message, question)

        # Do not reply to own bot messages
        if message.author.id == self.bot.user.id:
            return

        self.responder.history_manager.add_user_message(ctx.id, user_name, question)

        # Check auto memory update counter (every 10 messages)
        if message.guild and self.memory_service and getattr(self.responder, "use_server_memory", True):
            if self.memory_service.on_message_received(ctx.id):
                asyncio.create_task(self._auto_update_memory(ctx.id, ctx.name))

        # Do not reply to other bots unless listen_all_messages is True
        if message.author.bot and not self.listen_all_messages:
            return

        # Reply only if mentioned or listening to all messages
        if not (self.listen_all_messages or self.bot.user in message.mentions):
            return

        answer = await self.responder.get_answer(message, question)
        fake_interaction = InteractionAdapter.from_message(message)
        await self.playback_service.play_or_reply(
            interaction=fake_interaction,
            answer=answer,
            attach_audio_file=False,
            mention_user=self.mention_user
        )

    async def _auto_update_memory(self, guild_id: int, guild_name: str) -> None:
        """Background task to compact and update server memory without blocking chat."""
        try:
            if not self.memory_service:
                return
            history = self.responder.history_manager.get_latest_history(guild_id)
            if history:
                logger.info("Triggering auto memory consolidation for guild %s (%s)", guild_id, guild_name)
                await self.memory_service.consolidate_memory(
                    guild_id=guild_id,
                    guild_name=guild_name,
                    gemini_service=self.responder.gemini,
                    recent_messages=history
                )
        except Exception as exc:
            logger.error("Auto memory consolidation failed for guild %s: %s", guild_id, exc)

    @app_commands.command(name="q", description="Ask any question and get an AI-generated answer.")
    async def ask(self, interaction: discord.Interaction, text: str) -> None:
        await interaction.response.defer(thinking=True)
        answer = await self.responder.get_answer(interaction, text)
        await self.playback_service.play_or_reply(
            interaction=interaction,
            answer=answer,
            attach_audio_file=False,
            mention_user=self.mention_user
        )

    @app_commands.command(name="ask", description="Ask any question (alias of /q).")
    async def ask_alias(self, interaction: discord.Interaction, text: str) -> None:
        await self.ask(interaction, text)

    @app_commands.command(
        name="imginfo",
        description="Upload an image and get an AI description."
    )
    async def imginfo(
        self,
        interaction: discord.Interaction,
        image: discord.Attachment,
        text: str = ""
    ) -> None:
        await interaction.response.defer(thinking=True)
        if not image.content_type or not image.content_type.startswith("image/"):
            await interaction.followup.send("Please upload a valid image file.")
            return

        image_bytes = await image.read()
        answer = await self.responder.gemini.describe_image(
            image_bytes,
            mime_type=image.content_type,
            text=text
        )
        await self.playback_service.play_or_reply(
            interaction=interaction,
            answer=answer[:self.responder.gemini.max_len],
            attach_audio_file=False,
            mention_user=self.mention_user
        )

    @app_commands.command(
        name="fix_grammar",
        description="Fix grammar, spelling, and phrasing of your text."
    )
    async def fix_grammar(self, interaction: discord.Interaction, text: str) -> None:
        await interaction.response.defer(thinking=True)
        answer = await self.responder.gemini.fix_grammar(text)
        await self.playback_service.play_or_reply(
            interaction=interaction,
            answer=answer[:self.responder.gemini.max_len],
            attach_audio_file=False,
            mention_user=self.mention_user
        )


async def setup(bot: commands.Bot) -> None:
    responder = getattr(bot, "ai_responder", None)
    playback = getattr(bot, "playback_service", None)
    memory_service = getattr(bot, "memory_service", None)
    if responder and playback:
        await bot.add_cog(ChatCog(
            bot=bot,
            responder=responder,
            playback_service=playback,
            memory_service=memory_service
        ))

