"""AI-related slash commands using Gemini.
"""

from __future__ import annotations

from datetime import datetime
import io
import tempfile
from typing import Optional, DefaultDict, List, Tuple, Union
from collections import defaultdict
import os

import discord
from discord import app_commands
from discord.ext import commands

from services.gemini import GeminiService
from services.voicevox import VoiceVoxService
from services.voice_config import VoiceVoxConfig, VoiceVoxConfigKey
from services.ai_responder import AIResponder
from services.chat_history import ChatHistoryManager
from services.backup_service import BackupService

from utils.config import get_settings


import logging
import asyncio
import re

logger = logging.getLogger(__name__)

class AICog(commands.Cog):
    def __init__(self, bot: commands.Bot, responder: AIResponder, backup_service: BackupService):
        self.bot = bot
        self.responder = responder
        self.backup_service = backup_service

        # settings
        self.listen_all_messages = False  
        self.mention_user = True  
        self.backup_audio = True
        self.backup_text = True

    def _make_fake_interaction(self, message: discord.Message):
        class FakeFollowup:
            async def send(_, **kwargs):
                await message.channel.send(**kwargs)

        class FakeInteraction:
            def __init__(self, message):
                self.guild = message.guild
                self.user = message.author
                self.followup = FakeFollowup()

        return FakeInteraction(message)
    
    async def send_tts_response(
        self,
        interaction: discord.Interaction,
        answer: str,
        attach_audio_file: bool = True,
        mention_user: bool = True
    ):
        voicevox: VoiceVoxService = getattr(self.bot, "voicevox_service")
        wav_bytes = await voicevox.synthesize(answer)

        speaker_id = voicevox.default_speaker
        guild_id = interaction.guild.id if interaction.guild else 0  

        # Optionally prepend mention
        if mention_user:
            answer = f"<@{interaction.user.id}> {answer}"
        
        if self.backup_audio:
            self.backup_service.backup_audio(wav_bytes, speaker_id, guild_id)
        
        if self.backup_text:
            self.backup_service.backup_text(answer, speaker_id, guild_id)

        # Save TTS to a temporary file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(wav_bytes)
            tmp.flush()
            file_path = tmp.name

        file = discord.File(file_path, filename="response.wav")

        # Play in voice channel if connected
        voice_client: Optional[discord.VoiceClient] = discord.utils.get(
            self.bot.voice_clients, guild=interaction.guild
        )
        if voice_client and voice_client.is_connected():
            audio_source = discord.FFmpegPCMAudio(file_path)
            if voice_client.is_playing():
                voice_client.stop()
            voice_client.play(audio_source)

        # Send message with/without audio file
        send_kwargs = {"content": answer[:self.responder.gemini.max_len]}
        if attach_audio_file:
            send_kwargs["file"] = file

        await interaction.followup.send(**send_kwargs)



    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # すべてのメッセージを履歴に保存（botメッセージ含む）
        guild_id = message.guild.id if message.guild else 0
        guild_name = message.guild.name if message.guild else "DM"
        user_name = message.author.display_name
        self.responder.history_manager.add_user_message(guild_id, user_name, message.content)

        self.responder._log_interaction(message, message.content)

        # 自分のメッセージには返信しない
        if message.author.id == self.bot.user.id:
            return

        # 他botのメッセージは返信しない（ただし listen_all_messages が True の場合は返信する）
        if message.author.bot and not self.listen_all_messages:
            return

        # listen_all_messages が False なら、メンションがあるメッセージだけ返信
        if not (self.listen_all_messages or self.bot.user in message.mentions):
            return

        # メンション部分を除去して質問文を整形
        question = message.content.replace(f"<@{self.bot.user.id}>", "").strip() or "(Empty string)"
        answer = await self.responder.get_answer(message, question)

        fake_interaction = self._make_fake_interaction(message)
        await self.send_tts_response(fake_interaction, answer, attach_audio_file=False, mention_user=self.mention_user)

    @app_commands.command(name="toggle_mention", description="Toggle whether AI mentions the user in its replies.")
    async def toggle_mention(self, interaction: discord.Interaction):
        self.mention_user = not self.mention_user
        status = "mention users" if self.mention_user else "not mention users"
        await interaction.response.send_message(f"AI will now **{status}** in replies.")

    @app_commands.command(name="toggle_listen", description="Toggle AI to listen to all messages or only mentions.")
    async def toggle_listen(self, interaction: discord.Interaction):
        self.listen_all_messages = not self.listen_all_messages
        status = "all messages" if self.listen_all_messages else "only mentions"
        await interaction.response.send_message(f"AI will now listen to **{status}**.")

    @app_commands.command(name="toggle_backup_audio", description="Toggle whether AI saves generated audio files. ")
    async def toggle_backup_audio(self, interaction: discord.Interaction):
        self.backup_audio = not self.backup_audio
        status = "enabled" if self.backup_audio else "disabled"
        await interaction.response.send_message(f"Audio backup is now **{status}**.")

    @app_commands.command(name="toggle_backup_text", description="Toggle whether AI saves generated text files.")
    async def toggle_backup_text(self, interaction: discord.Interaction):
        self.backup_text = not self.backup_text
        status = "enabled" if self.backup_text else "disabled"
        await interaction.response.send_message(f"Text backup is now **{status}**.")

    @app_commands.command(name="q", description="Ask any question and get an AI-generated answer.")
    async def ask(self, interaction: discord.Interaction, text: str) -> None:
        await interaction.response.defer(thinking=True)
        answer = await self.responder.get_answer(interaction, text)
        await self.send_tts_response(interaction, answer, attach_audio_file=False, mention_user=self.mention_user)

    @app_commands.command(name="ask", description="Ask any question (alias of /q).")
    async def ask_alias(self, interaction: discord.Interaction, text: str) -> None:
        await interaction.response.defer(thinking=True)
        answer = await self.responder.get_answer(interaction, text)
        await self.send_tts_response(interaction, answer, attach_audio_file=False, mention_user=self.mention_user)


    @app_commands.command(
        name="voice",
        description="Ask a question and receive the answer as VoiceVox TTS audio.",
    )
    async def voice(self, interaction: discord.Interaction, text: str) -> None:
        await interaction.response.defer(thinking=True)
        answer = await self.responder.get_answer(interaction, text)
        await self.send_tts_response(interaction, answer, attach_audio_file=True, mention_user=self.mention_user)


    @app_commands.command(
        name="imginfo",
        description="Upload an image and get an AI description."
    )
    async def imginfo(self, interaction: discord.Interaction, image: discord.Attachment, text: str = "") -> None:
        await interaction.response.defer(thinking=True)
        if not image.content_type or not image.content_type.startswith("image/"):
            await interaction.followup.send("Please upload a valid image file.")
            return
        image_bytes = await image.read()
        answer = await self.responder.gemini.describe_image(image_bytes, mime_type=image.content_type, text=text)
        await self.send_tts_response(interaction, answer[:self.responder.gemini.max_len], attach_audio_file=False, mention_user=self.mention_user)

    @app_commands.command(
        name="fix_grammar",
        description="Fix grammar, spelling, and phrasing of your text.",
    )
    async def fix_grammar(self, interaction: discord.Interaction, text: str) -> None:
        await interaction.response.defer(thinking=True)
        answer = await self.responder.gemini.fix_grammar(text)
        await self.send_tts_response(interaction, answer[:self.responder.gemini.max_len], attach_audio_file=False, mention_user=self.mention_user)

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

        voice_client: Optional[discord.VoiceClient] = discord.utils.get(
            self.bot.voice_clients, guild=interaction.guild
        )
        if voice_client and voice_client.is_connected():
            if voice_client.channel.id != target.id:
                await voice_client.move_to(target)
        else:
            await target.connect()
        await interaction.followup.send(f"Joined voice channel: {target.name}")

    @app_commands.command(
        name="voice_channel_exit",
        description="Disconnect the bot from the current voice channel.",
    )
    async def voice_channel_exit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)
        voice_client: Optional[discord.VoiceClient] = discord.utils.get(
            self.bot.voice_clients, guild=interaction.guild
        )
        if not voice_client or not voice_client.is_connected():
            await interaction.followup.send("I'm not connected to a voice channel.")
            return
        await voice_client.disconnect(force=True)
        await interaction.followup.send("Disconnected from the voice channel.")

    @app_commands.command(
        name="change_speaker",
        description="Change the VoiceVox speaker id.",
    )
    async def change_speaker(self, interaction: discord.Interaction, speaker_id: int) -> None:
        await interaction.response.defer(thinking=True, ephemeral=False)
        voicevox: VoiceVoxService = getattr(self.bot, "voicevox_service")
        voicevox.default_speaker = speaker_id
        await interaction.followup.send(f"VoiceVox speaker changed to {speaker_id}.")

    @app_commands.command(
        name="reset_speaker",
        description="Reset the VoiceVox speaker id to the default.",
    )
    async def reset_speaker(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True, ephemeral=False)
        voicevox: VoiceVoxService = getattr(self.bot, "voicevox_service")
        settings = getattr(self.bot, "_settings", None)
        if settings is not None:
            voicevox.default_speaker = settings.voicevox_speaker
            await interaction.followup.send(f"VoiceVox speaker reset to default ({settings.voicevox_speaker}).")
        else:
            await interaction.followup.send("Could not reset speaker: default not found.")

    @app_commands.command(
        name="change_speed_scale",
        description="Change the VoiceVox speak speed",
    )
    async def change_speed_scale(self, interaction: discord.Interaction, speed: float) -> None:
        await interaction.response.defer(thinking=True, ephemeral=False)
        voicevox: VoiceVoxService = getattr(self.bot, "voicevox_service")
        voicevox.voicevox_config.set(VoiceVoxConfigKey.SPEED_SCALE, speed)
        await interaction.followup.send(
            f"VoiceVox speak speed scale changed to {voicevox.voicevox_config.get(VoiceVoxConfigKey.SPEED_SCALE)}."
        )

    @app_commands.command(
        name="change_pitch_scale",
        description="Change the VoiceVox pitch scale",
    )
    async def change_pitch_scale(self, interaction: discord.Interaction, pitch: float) -> None:
        await interaction.response.defer(thinking=True, ephemeral=False)
        voicevox: VoiceVoxService = getattr(self.bot, "voicevox_service")
        voicevox.voicevox_config.set(VoiceVoxConfigKey.PITCH_SCALE, pitch)
        await interaction.followup.send(
            f"VoiceVox pitch scale changed to {voicevox.voicevox_config.get(VoiceVoxConfigKey.PITCH_SCALE)}."
        )

    @app_commands.command(
        name="change_intonation_scale",
        description="Change the VoiceVox intonation scale",
    )
    async def change_intonation_scale(self, interaction: discord.Interaction, intonation: float) -> None:
        await interaction.response.defer(thinking=True, ephemeral=False)
        voicevox: VoiceVoxService = getattr(self.bot, "voicevox_service")
        voicevox.voicevox_config.set(VoiceVoxConfigKey.INTONATION_SCALE, intonation)
        await interaction.followup.send(
            f"VoiceVox intonation scale changed to {voicevox.voicevox_config.get(VoiceVoxConfigKey.INTONATION_SCALE)}."
        )

    @app_commands.command(
        name="change_volume_scale",
        description="Change the VoiceVox volume scale",
    )
    async def change_volume_scale(self, interaction: discord.Interaction, volume: float) -> None:
        await interaction.response.defer(thinking=True, ephemeral=False)
        voicevox: VoiceVoxService = getattr(self.bot, "voicevox_service")
        voicevox.voicevox_config.set(VoiceVoxConfigKey.VOLUME_SCALE, volume)
        await interaction.followup.send(
            f"VoiceVox volume scale changed to {voicevox.voicevox_config.get(VoiceVoxConfigKey.VOLUME_SCALE)}."
        )

    @app_commands.command(
        name="show_config",
        description="Show the current VoiceVox config",
    )
    async def show_config(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True, ephemeral=False)
        voicevox: VoiceVoxService = getattr(self.bot, "voicevox_service")
        config = voicevox.voicevox_config.as_dict()
        await interaction.followup.send(f"Current VoiceVox config: ```json\n{config}\n```")

    @app_commands.command(
        name="reset_config",
        description="Reset the VoiceVox config to defaults",
    )
    async def reset_config(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True, ephemeral=False)
        voicevox: VoiceVoxService = getattr(self.bot, "voicevox_service")
        voicevox.voicevox_config.reset()
        await interaction.followup.send("VoiceVox config has been reset to defaults.")

    @app_commands.command(
        name="change_pause_length_scale",
        description="Change the VoiceVox pause length scale",
    )
    async def change_pause_length_scale(self, interaction: discord.Interaction, pause_length_scale: float) -> None:
        await interaction.response.defer(thinking=True, ephemeral=False)
        voicevox: VoiceVoxService = getattr(self.bot, "voicevox_service")
        voicevox.voicevox_config.set(VoiceVoxConfigKey.PAUSE_LENGTH_SCALE, pause_length_scale)
        await interaction.followup.send(
            f"VoiceVox pause length scale changed to {voicevox.voicevox_config.get(VoiceVoxConfigKey.PAUSE_LENGTH_SCALE)}."
        )

    @app_commands.command(
        name="change_system_prompt",
        description="Change the system prompt for Gemini's responses."
    )
    async def change_system_prompt(self, interaction: discord.Interaction, prompt: str) -> None:
        self.responder.gemini._system_prompt = prompt
        await interaction.response.send_message(
            f"✅ System prompt updated.\nNew prompt:\n```{prompt}```"
        )

    @app_commands.command(
        name="change_gemini_model",
        description="Change the Gemini AI model used by the bot.",
    )
    @app_commands.describe(model="Select the Gemini model")
    @app_commands.choices(
        model=[app_commands.Choice(name=label, value=value) for label, value in GeminiService.list_available_models()]
    )
    async def change_gemini_model(self, interaction: discord.Interaction, model: app_commands.Choice[str]) -> None:
        await interaction.response.defer(thinking=True, ephemeral=False)
        gemini: GeminiService = getattr(self.bot, "gemini_service")
        gemini.model_text = model.value
        await interaction.followup.send(f"Gemini model changed to `{model.value}`.")

    @app_commands.command(
        name="set_history_length",
        description="Set how many previous messages are used for context."
    )
    @app_commands.describe(length="Number of messages to keep in context")
    async def set_history_length(self, interaction: discord.Interaction, length: int) -> None:
        if length < 1 or length > 50:
            await interaction.response.send_message("Please choose a value between 1 and 50.", ephemeral=True)
            return
        self.responder.history_manager.latest_n = length
        await interaction.response.send_message(f"History context length set to {length}.", ephemeral=False)

    @app_commands.command(
        name="clear_history",
        description="Clear your chat history with the AI."
    )
    async def clear_history(self, interaction: discord.Interaction) -> None:
        guild_id = interaction.guild.id if interaction.guild else 0
        self.responder.history_manager._history[guild_id].clear()
        await interaction.response.send_message("Your chat history has been cleared.", ephemeral=False)

    @app_commands.command(
        name="reset_system_prompt",
        description="Reset the system prompt for Gemini to the default."
    )
    async def reset_system_prompt(self, interaction: discord.Interaction) -> None:
        default_prompt = get_settings().system_prompt
        self.responder.gemini._system_prompt = default_prompt
        await interaction.response.send_message(
            "System prompt has been reset to the default.", ephemeral=False
        )

    @app_commands.command(
        name="reset_all",
        description="Reset all AI settings: history, system prompt, and VoiceVox config."
    )
    async def reset_all(self, interaction: discord.Interaction) -> None:
        guild_id = interaction.guild.id if interaction.guild else 0
        self.responder.history_manager._history[guild_id].clear()

        default_prompt = get_settings().system_prompt
        self.responder.gemini._system_prompt = default_prompt

        voicevox: VoiceVoxService = getattr(self.bot, "voicevox_service")
        voicevox.voicevox_config.reset()
        settings = getattr(self.bot, "_settings", None)
        if settings is not None:
            voicevox.default_speaker = settings.voicevox_speaker

        self.mention_user = True
        self.listen_all_messages = False

        await interaction.response.send_message(
            "All AI settings have been reset: chat history, system prompt, VoiceVox config, and speaker.", ephemeral=False
        )
    


async def setup(bot: commands.Bot) -> None:
    gemini: Optional[GeminiService] = getattr(bot, "gemini_service", None)
    if gemini is None:
        raise RuntimeError("GeminiService is not configured on the bot.")

    latest_n_history = get_settings().latest_n_history
    backup_dir = get_settings().backup_dir


    history_manager = ChatHistoryManager(latest_n=latest_n_history)
    ai_responder = AIResponder(gemini, history_manager, bot=bot)
    backup_service = BackupService(backup_dir)

    await bot.add_cog(AICog(
        bot=bot, 
        responder=ai_responder,
        backup_service=backup_service
    ))
