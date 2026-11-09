from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from services.providers.base import BaseAIProvider
from services.providers.factory import AIProviderFactory
from services.providers.gemini_provider import GeminiProvider
from utils.discord_context import GuildContext, require_service
from utils.interaction_adapter import InteractionAdapter
from services.voice_playback import VoicePlaybackService
from cogs.chat_cog import ChatCog
from cogs.voice_cog import VoiceCog
from cogs.voicevox_cog import VoiceVoxCog
from cogs.memory_cog import MemoryCog
from cogs.settings_cog import SettingsCog
from cogs.ai_cog import AICog


def test_ai_provider_factory():
    # Verify default registration
    assert "gemini" in AIProviderFactory.list_providers()

    # Create dummy provider
    class DummyProvider(BaseAIProvider):
        @property
        def provider_name(self) -> str:
            return "dummy"

        @property
        def model_name(self) -> str:
            return "dummy-model"

        @model_name.setter
        def model_name(self, value: str) -> None:
            pass

        @property
        def system_prompt(self) -> str:
            return ""

        @system_prompt.setter
        def system_prompt(self, value: str) -> None:
            pass

        async def ask_text(self, prompt, context_messages=None):
            return "dummy"

        async def ask_with_history(self, history, user_message, server_memory=None):
            return "dummy"

        async def describe_image(self, image_bytes, mime_type="image/png", text=""):
            return "dummy"

        async def fix_grammar(self, text: str):
            return text

        async def compact_memory_text(self, current_memory, recent_history_text, guild_name=""):
            return current_memory

        def list_available_models(self, only_gemini=False, exclude_pro=True):
            return [("Dummy", "dummy-model")]

    AIProviderFactory.register("dummy", DummyProvider)
    assert "dummy" in AIProviderFactory.list_providers()

    inst = AIProviderFactory.create("dummy")
    assert isinstance(inst, DummyProvider)
    assert inst.provider_name == "dummy"

    # Unknown provider raises ValueError
    with pytest.raises(ValueError):
        AIProviderFactory.create("non_existent_provider")


def test_guild_context():
    mock_interaction = MagicMock()
    mock_interaction.guild_id = 12345
    mock_interaction.guild.name = "MyGuild"

    ctx = GuildContext.from_interaction(mock_interaction)
    assert ctx.id == 12345
    assert ctx.name == "MyGuild"

    # Direct Message
    mock_dm = MagicMock()
    mock_dm.guild_id = None
    mock_dm.guild = None
    ctx_dm = GuildContext.from_interaction(mock_dm)
    assert ctx_dm.id == 0
    assert ctx_dm.name == "Direct Message"


@pytest.mark.asyncio
async def test_require_service():
    mock_interaction = MagicMock()
    mock_interaction.response.is_done.return_value = False
    mock_interaction.response.send_message = AsyncMock()

    # When service is available
    res = await require_service(mock_interaction, "existing_service", "Test Service")
    assert res == "existing_service"
    mock_interaction.response.send_message.assert_not_called()

    # When service is None
    res_none = await require_service(mock_interaction, None, "Missing Service")
    assert res_none is None
    mock_interaction.response.send_message.assert_awaited_once()
    assert "Missing Service" in mock_interaction.response.send_message.call_args[0][0]


def test_interaction_adapter():
    mock_msg = MagicMock()
    mock_msg.guild.id = 777
    mock_msg.guild.name = "AdapterGuild"
    mock_msg.author.display_name = "User123"

    adapter = InteractionAdapter.from_message(mock_msg)
    assert adapter.guild_id == 777
    assert adapter.guild.name == "AdapterGuild"
    assert adapter.user.display_name == "User123"


def test_cogs_instantiation():
    mock_bot = MagicMock()
    mock_bot.voice_clients = []
    mock_responder = MagicMock()
    mock_playback = MagicMock()
    mock_memory = MagicMock()
    mock_voicevox = MagicMock()
    mock_backup = MagicMock()

    chat_cog = ChatCog(mock_bot, mock_responder, mock_playback, mock_memory)
    assert chat_cog.bot == mock_bot

    voice_cog = VoiceCog(mock_bot, mock_responder, mock_playback)
    assert voice_cog.bot == mock_bot

    voicevox_cog = VoiceVoxCog(mock_bot, mock_voicevox)
    assert voicevox_cog.bot == mock_bot

    memory_cog = MemoryCog(mock_bot, mock_memory, mock_responder)
    assert memory_cog.bot == mock_bot

    settings_cog = SettingsCog(mock_bot, mock_responder, mock_playback, mock_voicevox)
    assert settings_cog.bot == mock_bot

    ai_cog = AICog(mock_bot, mock_responder, mock_backup, mock_memory, mock_playback)
    assert ai_cog.use_server_memory is True

