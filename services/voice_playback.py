from __future__ import annotations

import logging
import os
import tempfile
from typing import Optional, Union
import discord

from services.backup_service import BackupService
from services.voicevox import VoiceVoxService

logger = logging.getLogger(__name__)


class VoicePlaybackService:
    """Service / Facade Pattern for VoiceVox TTS synthesis, audio backup, and voice channel playback."""

    def __init__(
        self,
        bot: discord.Client,
        voicevox_service: Optional[VoiceVoxService] = None,
        backup_service: Optional[BackupService] = None,
        backup_audio: bool = True,
        backup_text: bool = True,
        max_len: int = 1900
    ) -> None:
        self.bot = bot
        self.voicevox_service = voicevox_service
        self.backup_service = backup_service
        self.backup_audio = backup_audio
        self.backup_text = backup_text
        self.max_len = max_len

    async def play_or_reply(
        self,
        interaction: Union[discord.Interaction, Any],
        answer: str,
        attach_audio_file: bool = True,
        mention_user: bool = True
    ) -> None:
        """Synthesize VoiceVox audio, stream to connected voice channel, and send reply."""
        wav_bytes: Optional[bytes] = None
        if self.voicevox_service is not None:
            try:
                wav_bytes = await self.voicevox_service.synthesize(answer)
            except Exception as exc:
                logger.warning("VoiceVox synthesis error: %s. Falling back to text-only.", exc)
                wav_bytes = None

        speaker_id = self.voicevox_service.default_speaker if self.voicevox_service else 1
        guild_id = interaction.guild.id if interaction.guild else 0

        # Optionally prepend user mention
        content = answer
        if mention_user and hasattr(interaction, "user") and interaction.user:
            content = f"<@{interaction.user.id}> {answer}"

        # Text backup
        if self.backup_text and self.backup_service:
            self.backup_service.backup_text(content, speaker_id, guild_id)

        send_kwargs = {"content": content[:self.max_len]}

        if wav_bytes:
            # Audio backup (auto-compressed to MP3)
            if self.backup_audio and self.backup_service:
                self.backup_service.backup_audio(wav_bytes, speaker_id, guild_id)

            # Write TTS audio to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(wav_bytes)
                tmp.flush()
                file_path = tmp.name

            file = discord.File(file_path, filename="response.wav")

            # Stream to voice channel if bot is currently connected in this guild
            voice_client: Optional[discord.VoiceClient] = discord.utils.get(
                self.bot.voice_clients, guild=interaction.guild
            )

            def _cleanup_tmp(err=None):
                if err:
                    logger.warning("Audio playback error: %s", err)
                try:
                    if os.path.exists(file_path):
                        os.unlink(file_path)
                except Exception:
                    pass

            played_in_vc = False
            if voice_client and voice_client.is_connected():
                audio_source = discord.FFmpegPCMAudio(file_path)
                if voice_client.is_playing():
                    voice_client.stop()
                voice_client.play(audio_source, after=_cleanup_tmp)
                played_in_vc = True

            if attach_audio_file:
                send_kwargs["file"] = file
        else:
            if attach_audio_file:
                logger.info("VoiceVox audio not available; sending text-only response.")

        await interaction.followup.send(**send_kwargs)

        if wav_bytes and not played_in_vc:
            _cleanup_tmp()

