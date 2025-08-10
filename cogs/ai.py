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

try:
    import edge_tts  # type: ignore
except Exception:  # pragma: no cover - optional at runtime
    edge_tts = None


class AICog(commands.Cog):
    """Cog providing AI-related slash commands."""

    def __init__(self, bot: commands.Bot, gemini: GeminiService) -> None:
        self.bot = bot
        self.gemini = gemini
        # Simple in-memory chat history mapping user_id to [(role, content), ...]
        self._history: DefaultDict[int, List[Tuple[str, str]]] = defaultdict(list)

    async def _answer_question(self, user_id: int, question: str) -> str:
        """Generate an answer using short rolling history and store the exchange."""
        history = self._history[user_id][-6:]
        answer = await self.gemini.ask_with_history(history, question)
        self._history[user_id].append(("user", question))
        self._history[user_id].append(("model", answer))

        print(f"user_id: {user_id}")
        print(f"all_history: {self._history[user_id]}")
        print(f"history: {history}")

        return answer

    @app_commands.command(name="q", description="Ask any question and get an AI-generated answer.")
    async def ask(self, interaction: discord.Interaction, text: str) -> None:
        await interaction.response.defer(thinking=True)
        answer = await self._answer_question(interaction.user.id, text)
        await self.play_tts(interaction, answer, attach_audio_file=False)


    @app_commands.command(name="ask", description="Ask any question (alias of /q).")
    async def ask_alias(self, interaction: discord.Interaction, text: str) -> None:
        await interaction.response.defer(thinking=True)
        answer = await self._answer_question(interaction.user.id, text)
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
        answer = await self._answer_question(interaction.user.id, question)
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
        description="Change the default VoiceVox speaker id.",
    )
    async def change_speaker(self, interaction: discord.Interaction, speaker_id: int) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)
        voicevox: VoiceVoxService = getattr(self.bot, "voicevox_service")
        voicevox.default_speaker = speaker_id
        await interaction.followup.send(f"VoiceVox speaker changed to {speaker_id}.")

    @app_commands.command(
        name="change_system_prompt",
        description="Change the system prompt for Gemini's responses."
    )
    async def change_system_prompt(self, interaction: discord.Interaction, prompt: str) -> None:
        self.gemini._system_prompt = prompt
        await interaction.response.send_message(
            f"✅ System prompt updated.\nNew prompt:\n```{prompt}```"
        )

    # @app_commands.command(
    #     name="voice_edge_tts",
    #     description="Ask a question and receive the answer as spoken audio.",
    # )
    # async def voice_edge_tts(self, interaction: discord.Interaction, question: str) -> None:
    #     await interaction.response.defer(thinking=True)
    #     answer = await self._answer_question(interaction.user.id, question)

    #     if edge_tts is None:
    #         await interaction.followup.send(
    #             "Text-to-speech engine is not available. Install edge-tts to enable this command."
    #         )
    #         return

    #     # Generate TTS audio using Edge TTS and send as attachment
    #     communicate = edge_tts.Communicate(answer, voice="en-US-JennyNeural")
    #     with tempfile.NamedTemporaryFile(suffix=".mp3", delete=True) as tmp:
    #         await communicate.save(tmp.name)
    #         tmp.seek(0)
    #         file = discord.File(tmp.name, filename="response.mp3")
    #         await interaction.followup.send(content=answer[:self.gemini.max_len], file=file)


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

