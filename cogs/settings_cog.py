from __future__ import annotations

import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from services.ai_responder import AIResponder
from services.voicevox import VoiceVoxService
from services.voice_playback import VoicePlaybackService
from services.gemini import GeminiService
from utils.discord_context import GuildContext, require_service

logger = logging.getLogger(__name__)


class SettingsCog(commands.Cog, name="Settings"):
    """Cog for managing AI models, persona prompts, history window, and session toggles."""

    def __init__(
        self,
        bot: commands.Bot,
        responder: AIResponder,
        playback_service: VoicePlaybackService,
        voicevox_service: Optional[VoiceVoxService] = None
    ) -> None:
        self.bot = bot
        self.responder = responder
        self.playback_service = playback_service
        self.voicevox_service = voicevox_service
        self.listen_all_messages = False
        self.mention_user = True

    @app_commands.command(
        name="change_system_prompt",
        description="Change the AI system prompt/persona.",
    )
    async def change_system_prompt(self, interaction: discord.Interaction, prompt: str) -> None:
        await interaction.response.defer(thinking=True, ephemeral=False)
        self.responder.gemini.system_prompt = prompt
        await interaction.followup.send(f"System prompt updated:\n`{prompt}`")

    @app_commands.command(
        name="reset_system_prompt",
        description="Reset the AI system prompt/persona to the default value.",
    )
    async def reset_system_prompt(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True, ephemeral=False)
        settings = getattr(self.bot, "_settings", None)
        default_prompt = settings.system_prompt if settings else ""
        self.responder.gemini.system_prompt = default_prompt
        await interaction.followup.send("System prompt reset to default.")

    @app_commands.command(
        name="change_gemini_model",
        description="Change the active Gemini/Gemma model.",
    )
    @app_commands.describe(model="Select a Gemini/Gemma model to use.")
    @app_commands.choices(
        model=[
            app_commands.Choice(name=label, value=value)
            for label, value in GeminiService.list_available_models()
        ]
    )
    async def change_gemini_model(
        self,
        interaction: discord.Interaction,
        model: app_commands.Choice[str]
    ) -> None:
        await interaction.response.defer(thinking=True, ephemeral=False)
        self.responder.gemini.model_text = model.value
        await interaction.followup.send(f"Gemini model changed to **{model.name}** (`{model.value}`).")

    @app_commands.command(
        name="set_history_length",
        description="Set how many recent messages to remember (1 to 50).",
    )
    async def set_history_length(self, interaction: discord.Interaction, length: int) -> None:
        await interaction.response.defer(thinking=True, ephemeral=False)
        if 1 <= length <= 50:
            self.responder.history_manager.latest_n = length
            await interaction.followup.send(f"History length set to **{length}**.")
        else:
            await interaction.followup.send("Please provide a number between 1 and 50.")

    @app_commands.command(
        name="clear_history",
        description="Clear conversation history for this server.",
    )
    async def clear_history(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True, ephemeral=False)
        ctx = GuildContext.from_interaction(interaction)
        self.responder.history_manager._history[ctx.id] = []
        await interaction.followup.send("Conversation history cleared.")

    @app_commands.command(
        name="reset_all",
        description="Reset history, system prompt, VoiceVox config, and speaker to defaults.",
    )
    async def reset_all(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True, ephemeral=False)
        ctx = GuildContext.from_interaction(interaction)
        self.responder.history_manager._history[ctx.id] = []

        settings = getattr(self.bot, "_settings", None)
        if settings:
            self.responder.gemini.system_prompt = settings.system_prompt or ""
            if self.voicevox_service:
                self.voicevox_service.default_speaker = settings.voicevox_speaker
                self.voicevox_service.voicevox_config.reset_to_default()

        await interaction.followup.send("All configurations have been reset to default values.")

    @app_commands.command(name="toggle_mention", description="Toggle whether AI mentions the user in replies.")
    async def toggle_mention(self, interaction: discord.Interaction) -> None:
        self.mention_user = not self.mention_user
        status = "mention users" if self.mention_user else "not mention users"
        await interaction.response.send_message(f"AI will now **{status}** in replies.")

    @app_commands.command(name="toggle_listen", description="Toggle AI to listen to all messages or only mentions.")
    async def toggle_listen(self, interaction: discord.Interaction) -> None:
        self.listen_all_messages = not self.listen_all_messages
        status = "all messages" if self.listen_all_messages else "only mentions"
        await interaction.response.send_message(f"AI will now listen to **{status}**.")

    @app_commands.command(name="toggle_backup_audio", description="Toggle whether AI saves generated audio files.")
    async def toggle_backup_audio(self, interaction: discord.Interaction) -> None:
        self.playback_service.backup_audio = not self.playback_service.backup_audio
        status = "enabled" if self.playback_service.backup_audio else "disabled"
        await interaction.response.send_message(f"Audio backup is now **{status}**.")

    @app_commands.command(name="toggle_backup_text", description="Toggle whether AI saves generated text files.")
    async def toggle_backup_text(self, interaction: discord.Interaction) -> None:
        self.playback_service.backup_text = not self.playback_service.backup_text
        status = "enabled" if self.playback_service.backup_text else "disabled"
        await interaction.response.send_message(f"Text backup is now **{status}**.")

    @app_commands.command(
        name="help",
        description="List all available commands and their descriptions."
    )
    async def help_command(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="📖 Discord AI Assistant Bot - Command List",
            description="All available slash commands grouped by category:",
            color=0x4A90E2
        )
        embed.add_field(
            name="🤖 AI Chat & Tasks",
            value=(
                "• `/q <text>` - Ask the AI any question\n"
                "• `/ask <text>` - Alias for `/q`\n"
                "• `/voice <text>` - Ask a question and get TTS voice audio reply\n"
                "• `/imginfo <image> [text]` - Upload image for AI analysis\n"
                "• `/fix_grammar <text>` - Correct grammar, spelling, and phrasing"
            ),
            inline=False
        )
        embed.add_field(
            name="🔊 Voice Channel",
            value=(
                "• `/voice_channel_join [channel]` - Bot joins your voice channel\n"
                "• `/voice_channel_exit` - Bot disconnects from voice channel"
            ),
            inline=False
        )
        embed.add_field(
            name="🎙️ VOICEVOX TTS Settings",
            value=(
                "• `/change_speaker <id>` - Change VoiceVox speaker ID\n"
                "• `/reset_speaker` - Reset speaker ID to default\n"
                "• `/change_speed_scale <speed>` - Adjust speaking speed\n"
                "• `/change_pitch_scale <pitch>` - Adjust voice pitch\n"
                "• `/change_intonation_scale <scale>` - Adjust intonation\n"
                "• `/change_volume_scale <volume>` - Adjust speech volume\n"
                "• `/change_pause_length_scale <scale>` - Adjust pause duration\n"
                "• `/show_config` - View current VoiceVox configuration\n"
                "• `/reset_config` - Reset VoiceVox settings to defaults"
            ),
            inline=False
        )
        embed.add_field(
            name="🧠 Server Memory",
            value=(
                "• `/memory show` - Display current server memory (memory.md)\n"
                "• `/memory add <note>` - Add a custom note/fact to server memory\n"
                "• `/memory clear` - Reset server memory to defaults\n"
                "• `/memory update` - Consolidate recent conversations into memory\n"
                "• `/toggle_memory` - Toggle persistent server memory injection"
            ),
            inline=False
        )
        embed.add_field(
            name="⚙️ Bot & Session Configuration",
            value=(
                "• `/change_gemini_model <model>` - Switch active Gemini/Gemma AI model\n"
                "• `/change_system_prompt <prompt>` - Change AI persona/system prompt\n"
                "• `/reset_system_prompt` - Reset persona to default\n"
                "• `/set_history_length <length>` - Set context history window size\n"
                "• `/clear_history` - Clear conversation history\n"
                "• `/reset_all` - Reset history, persona, and VoiceVox configs\n"
                "• `/toggle_mention` - Toggle user mention in replies\n"
                "• `/toggle_listen` - Toggle reply to all messages vs mentions only\n"
                "• `/toggle_backup_audio` - Toggle audio file backup\n"
                "• `/toggle_backup_text` - Toggle chat text backup\n"
                "• `/help` - Show this command list"
            ),
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)


async def setup(bot: commands.Bot) -> None:
    responder = getattr(bot, "ai_responder", None)
    playback = getattr(bot, "playback_service", None)
    voicevox = getattr(bot, "voicevox_service", None)
    if responder and playback:
        await bot.add_cog(SettingsCog(
            bot=bot,
            responder=responder,
            playback_service=playback,
            voicevox_service=voicevox
        ))

