"""AI-related slash commands using Gemini.
"""

from __future__ import annotations

import io
import tempfile
from typing import Optional, DefaultDict, List, Tuple
from collections import defaultdict
import os

import discord
from discord import app_commands
from discord.ext import commands

from services.gemini import GeminiService
from services.voicevox import VoiceVoxService
from services.voice_config import VoiceVoxConfig, VoiceVoxConfigKey
from utils.config import Settings

try:
    import edge_tts  # type: ignore
except Exception:  # pragma: no cover - optional at runtime
    edge_tts = None


class AICog(commands.Cog):
    """Cog providing AI-related slash commands."""

    def __init__(self, bot: commands.Bot, gemini: GeminiService, latest_n_history: int = 10) -> None:
        self.bot = bot
        self.gemini = gemini
        self.latest_n_history = int(os.getenv("LATEST_N_HISTORY", "10"))
        # Simple in-memory chat history mapping user_id to [(role, content), ...]
        # Structure: {guild_id: [history_list]}
        self._history: DefaultDict[int, List[dict]] = defaultdict(list)

    def get_latest_history(self, user_id: int) -> List[dict]:
        """Return the latest N messages for a user."""
        return self._history[user_id][-self.latest_n_history:]

    async def _answer_question(self, interaction: discord.Interaction, question: str) -> str:
        """Generate an answer using short rolling history and store the exchange."""
        guild_id = interaction.guild.id if interaction.guild else 0
        user_id = interaction.user.id
        history = self._history[guild_id][-self.latest_n_history:]
        answer = await self.gemini.ask_with_history(history, question)
        self._history[guild_id].append({"role": "user", "content": question})
        self._history[guild_id].append({"role": "assistant", "content": answer})

        print(f"\n\tuser_id: {user_id}")

        # print(f"\tall_history: {self._history[user_id]}")
        print(f"\tall_user_history: {self._history}")

        print(f"\tlastest_history: {history}")

        return answer

    @app_commands.command(name="q", description="Ask any question and get an AI-generated answer.")
    async def ask(self, interaction: discord.Interaction, text: str) -> None:
        await interaction.response.defer(thinking=True)
        answer = await self._answer_question(interaction, text)
        await self.play_tts(interaction, answer, attach_audio_file=False)


    @app_commands.command(name="ask", description="Ask any question (alias of /q).")
    async def ask_alias(self, interaction: discord.Interaction, text: str) -> None:
        await interaction.response.defer(thinking=True)
        answer = await self._answer_question(interaction, text)
        await self.play_tts(interaction, answer, attach_audio_file=False)

    @app_commands.command(name="imginfo", description="Upload an image and get an AI description.")
    async def imginfo(self, interaction: discord.Interaction, image: discord.Attachment, text: str = "") -> None:
        await interaction.response.defer(thinking=True)
        if not image.content_type or not image.content_type.startswith("image/"):
            await interaction.followup.send("Please upload a valid image file.")
            return
        image_bytes = await image.read()
        answer = await self.gemini.describe_image(image_bytes, mime_type=image.content_type, text=text)
        await self.play_tts(interaction, answer[:self.gemini.max_len], attach_audio_file=False)

    @app_commands.command(
        name="fix_grammar",
        description="Fix grammar, spelling, and phrasing of your text.",
    )
    async def fix_grammar(self, interaction: discord.Interaction, text: str) -> None:
        await interaction.response.defer(thinking=True)
        answer = await self.gemini.fix_grammar(text)
        await self.play_tts(interaction, answer[:self.gemini.max_len], attach_audio_file=False)


    @app_commands.command(
        name="voice",
        description="Ask a question and receive the answer as VoiceVox TTS audio.",
    )
    async def voice(self, interaction: discord.Interaction, question: str) -> None:
        await interaction.response.defer(thinking=True)
        answer = await self._answer_question(interaction, question)
        await self.play_tts(interaction, answer, attach_audio_file=True)

    @app_commands.command(
        name="voice_channel_join",
        description="Make the bot join your current voice channel or the specified one.",
    )
    async def voice_channel_join(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.VoiceChannel] = None,
    ) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)
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
        await interaction.followup.send(f"VoiceVox speak speed scale changed to {voicevox.voicevox_config.get(VoiceVoxConfigKey.SPEED_SCALE)}.")

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
        await interaction.response.defer(thinking=True, ephemeral=True)
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
        self.gemini._system_prompt = prompt
        await interaction.response.send_message(
            f"✅ System prompt updated.\nNew prompt:\n```{prompt}```"
        )

    @app_commands.command(
        name="change_gemini_model",
        description="Change the Gemini AI model used by the bot.",
    )
    @app_commands.describe(model="Select the Gemini model")
    @app_commands.choices( model=[ app_commands.Choice(name=label, value=value) for label, value in  GeminiService.list_available_models()])
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
        self.latest_n_history = length
        await interaction.response.send_message(f"History context length set to {length}.", ephemeral=True)

    @app_commands.command(
        name="clear_history",
        description="Clear your chat history with the AI."
    )
    async def clear_history(self, interaction: discord.Interaction) -> None:
        user_id = interaction.user.id
        self._history[interaction.guild.id].clear()
        await interaction.response.send_message("Your chat history has been cleared.", ephemeral=True)

    @app_commands.command(
        name="reset_system_prompt",
        description="Reset the system prompt for Gemini to the default."
    )
    async def reset_system_prompt(self, interaction: discord.Interaction) -> None:
        from utils.config import get_settings
        default_prompt = get_settings().system_prompt
        self.gemini._system_prompt = default_prompt
        await interaction.response.send_message(
            "System prompt has been reset to the default.", ephemeral=True
        )

    @app_commands.command(
        name="reset_all",
        description="Reset all AI settings: history, system prompt, and VoiceVox config."
    )
    async def reset_all(self, interaction: discord.Interaction) -> None:
        user_id = interaction.user.id
        self._history[interaction.guild.id].clear()
        from utils.config import get_settings
        default_prompt = get_settings().system_prompt
        self.gemini._system_prompt = default_prompt
        voicevox: VoiceVoxService = getattr(self.bot, "voicevox_service")
        voicevox.voicevox_config.reset()
        settings = getattr(self.bot, "_settings", None)
        if settings is not None:
            voicevox.default_speaker = settings.voicevox_speaker
        await interaction.response.send_message(
            "All AI settings have been reset: chat history, system prompt, VoiceVox config, and speaker.", ephemeral=True
        )


    async def play_tts(self,interaction: discord.Interaction, answer: str, attach_audio_file: bool = True): 
        voicevox: VoiceVoxService = getattr(self.bot, "voicevox_service")
        wav_bytes = await voicevox.synthesize(answer)

        voice_client: Optional[discord.VoiceClient] = discord.utils.get(
            self.bot.voice_clients, guild=interaction.guild
        )

        if voice_client and voice_client.is_connected():
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(wav_bytes)
                tmp.flush()
                audio_source = discord.FFmpegPCMAudio(tmp.name)
                if voice_client.is_playing():
                    voice_client.stop()
                voice_client.play(audio_source)
                # voice_client.play(audio_source, after=lambda e: os.remove(tmp_path))

                file = discord.File(tmp.name, filename="response.wav")
                if attach_audio_file: 
                    await interaction.followup.send( content=( answer[:self.gemini.max_len]), file=file)
                else:
                    await interaction.followup.send( content=( answer[:self.gemini.max_len]))


        else:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(wav_bytes)
                tmp.flush()
                file = discord.File(tmp.name, filename="response.wav")

                if attach_audio_file: 
                    await interaction.followup.send( content=( answer[:self.gemini.max_len]), file=file)
                else:
                    await interaction.followup.send( content=( answer[:self.gemini.max_len]))

async def setup(bot: commands.Bot) -> None:
    # The bot will inject a configured GeminiService via bot state.
    gemini: Optional[GeminiService] = getattr(bot, "gemini_service", None)
    if gemini is None:
        raise RuntimeError("GeminiService is not configured on the bot.")
    await bot.add_cog(AICog(bot, gemini))

