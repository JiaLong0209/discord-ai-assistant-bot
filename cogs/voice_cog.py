from __future__ import annotations

import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from services.ai_responder import AIResponder
from services.voice_playback import VoicePlaybackService
from utils.discord_context import require_service

logger = logging.getLogger(__name__)


class VoiceCog(commands.Cog, name="Voice"):
    """Cog for managing Discord voice channel connections and voice TTS responses."""

    def __init__(
        self,
        bot: commands.Bot,
        responder: AIResponder,
        playback_service: VoicePlaybackService
    ) -> None:
        self.bot = bot
        self.responder = responder
        self.playback_service = playback_service
        self.mention_user = True

    @app_commands.command(
        name="voice",
        description="Ask a question and receive the answer as VoiceVox TTS audio.",
    )
    async def voice(self, interaction: discord.Interaction, text: str) -> None:
        await interaction.response.defer(thinking=True)
        answer = await self.responder.get_answer(interaction, text)
        await self.playback_service.play_or_reply(
            interaction=interaction,
            answer=answer,
            attach_audio_file=True,
            mention_user=self.mention_user
        )

    @app_commands.command(
        name="voice_channel_join",
        description="Make the bot join your current voice channel or the specified one.",
    )
    async def voice_channel_join(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.VoiceChannel] = None,
    ) -> None:
        await interaction.response.defer(thinking=True, ephemeral=False)
        target = channel
        if target is None:
            if not interaction.user or not isinstance(interaction.user, discord.Member):
                await interaction.followup.send("Cannot determine your voice state.")
                return
            if not interaction.user.voice or not interaction.user.voice.channel:
                await interaction.followup.send("Join a voice channel first or specify one.")
                return
            target = interaction.user.voice.channel

        guild = interaction.guild
        if guild is None:
            await interaction.followup.send("This command must be used in a server.")
            return

        voice_client: Optional[discord.VoiceClient] = guild.voice_client
        try:
            if voice_client:
                if voice_client.is_connected():
                    if voice_client.channel.id != target.id:
                        await voice_client.move_to(target)
                        await interaction.followup.send(f"🔊 Moved to voice channel: **{target.name}**")
                    else:
                        await interaction.followup.send(f"🔊 Already connected to **{target.name}**")
                    return
                else:
                    logger.warning("Clearing stale voice client before reconnecting...")
                    await voice_client.disconnect(force=True)

            await target.connect(reconnect=True, timeout=20.0)
            await interaction.followup.send(f"🔊 Connected to voice channel: **{target.name}**")
        except Exception as e:
            logger.exception("Failed to connect to voice channel %s: %s", target.name, e)
            if guild.voice_client:
                try:
                    await guild.voice_client.disconnect(force=True)
                except Exception:
                    pass
            await interaction.followup.send(f"⚠️ Failed to connect to voice channel: `{e}`")

    @app_commands.command(
        name="voice_channel_exit",
        description="Disconnect the bot from the current voice channel.",
    )
    async def voice_channel_exit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True, ephemeral=False)
        guild = interaction.guild
        voice_client: Optional[discord.VoiceClient] = guild.voice_client if guild else None
        if not voice_client:
            await interaction.followup.send("I'm not connected to a voice channel.")
            return
        channel_name = voice_client.channel.name if voice_client.channel else "voice channel"
        await voice_client.disconnect(force=True)
        await interaction.followup.send(f"👋 Disconnected from **{channel_name}**.")


async def setup(bot: commands.Bot) -> None:
    responder = getattr(bot, "ai_responder", None)
    playback = getattr(bot, "playback_service", None)
    if responder and playback:
        await bot.add_cog(VoiceCog(bot=bot, responder=responder, playback_service=playback))

