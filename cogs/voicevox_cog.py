from __future__ import annotations

import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from services.voicevox import VoiceVoxService
from services.voice_config import VoiceVoxConfig, VoiceVoxConfigKey
from utils.discord_context import require_service

logger = logging.getLogger(__name__)


class VoiceVoxCog(commands.Cog, name="VoiceVox"):
    """Cog for managing VoiceVox TTS parameters and configurations."""

    def __init__(
        self,
        bot: commands.Bot,
        voicevox_service: Optional[VoiceVoxService] = None,
        default_speaker: int = 1
    ) -> None:
        self.bot = bot
        self.voicevox_service = voicevox_service
        self.default_speaker = default_speaker

    @app_commands.command(
        name="change_speaker",
        description="Change the VoiceVox speaker id.",
    )
    async def change_speaker(self, interaction: discord.Interaction, speaker_id: int) -> None:
        if not await require_service(interaction, self.voicevox_service, "VoiceVox service"):
            return
        await interaction.response.defer(thinking=True, ephemeral=False)
        self.voicevox_service.default_speaker = speaker_id
        await interaction.followup.send(f"VoiceVox speaker changed to {speaker_id}.")

    @app_commands.command(
        name="reset_speaker",
        description="Reset the VoiceVox speaker id to the default.",
    )
    async def reset_speaker(self, interaction: discord.Interaction) -> None:
        if not await require_service(interaction, self.voicevox_service, "VoiceVox service"):
            return
        await interaction.response.defer(thinking=True, ephemeral=False)
        self.voicevox_service.default_speaker = self.default_speaker
        await interaction.followup.send(f"VoiceVox speaker reset to default ({self.default_speaker}).")

    async def _update_scale_config(
        self,
        interaction: discord.Interaction,
        key: VoiceVoxConfigKey,
        value: float,
        name: str
    ) -> None:
        if not await require_service(interaction, self.voicevox_service, "VoiceVox service"):
            return
        await interaction.response.defer(thinking=True, ephemeral=False)
        self.voicevox_service.voicevox_config.update(key, value)
        await interaction.followup.send(f"VoiceVox {name} changed to {value}.")

    @app_commands.command(name="change_speed_scale", description="Change VoiceVox speech speed.")
    async def change_speed_scale(self, interaction: discord.Interaction, speed: float) -> None:
        await self._update_scale_config(interaction, VoiceVoxConfigKey.SPEED_SCALE, speed, "speed scale")

    @app_commands.command(name="change_pitch_scale", description="Change VoiceVox pitch.")
    async def change_pitch_scale(self, interaction: discord.Interaction, pitch: float) -> None:
        await self._update_scale_config(interaction, VoiceVoxConfigKey.PITCH_SCALE, pitch, "pitch scale")

    @app_commands.command(name="change_intonation_scale", description="Change VoiceVox intonation.")
    async def change_intonation_scale(self, interaction: discord.Interaction, intonation: float) -> None:
        await self._update_scale_config(interaction, VoiceVoxConfigKey.INTONATION_SCALE, intonation, "intonation scale")

    @app_commands.command(name="change_volume_scale", description="Change VoiceVox volume.")
    async def change_volume_scale(self, interaction: discord.Interaction, volume: float) -> None:
        await self._update_scale_config(interaction, VoiceVoxConfigKey.VOLUME_SCALE, volume, "volume scale")

    @app_commands.command(name="change_pause_length_scale", description="Change VoiceVox pause length scale.")
    async def change_pause_length_scale(self, interaction: discord.Interaction, pause_length_scale: float) -> None:
        await self._update_scale_config(interaction, VoiceVoxConfigKey.PAUSE_LENGTH_SCALE, pause_length_scale, "pause length scale")

    @app_commands.command(name="show_config", description="Show current VoiceVox configuration.")
    async def show_config(self, interaction: discord.Interaction) -> None:
        if not await require_service(interaction, self.voicevox_service, "VoiceVox service"):
            return
        await interaction.response.defer(thinking=True, ephemeral=False)
        config_data = self.voicevox_service.voicevox_config.to_dict()
        formatted = "\n".join([f"**{k}**: {v}" for k, v in config_data.items()])
        await interaction.followup.send(f"Current VoiceVox Configuration:\n{formatted}")

    @app_commands.command(name="reset_config", description="Reset VoiceVox configuration to defaults.")
    async def reset_config(self, interaction: discord.Interaction) -> None:
        if not await require_service(interaction, self.voicevox_service, "VoiceVox service"):
            return
        await interaction.response.defer(thinking=True, ephemeral=False)
        self.voicevox_service.voicevox_config.reset_to_default()
        await interaction.followup.send("VoiceVox configuration reset to default.")


async def setup(bot: commands.Bot) -> None:
    voicevox = getattr(bot, "voicevox_service", None)
    settings = getattr(bot, "_settings", None)
    default_speaker = settings.voicevox_speaker if settings else 1
    await bot.add_cog(VoiceVoxCog(bot=bot, voicevox_service=voicevox, default_speaker=default_speaker))

