from __future__ import annotations

import os
import shutil
import tempfile
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.memory_service import MemoryService
from services.gemini import GeminiService
from services.ai_responder import AIResponder
from services.chat_history import ChatHistoryManager
from cogs.ai_cog import AICog


@pytest.fixture
def temp_memory_dir():
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_default_memory_creation(temp_memory_dir):
    service = MemoryService(base_dir=temp_memory_dir, update_interval=10)
    guild_id = 987654321
    guild_name = "Test Discord Server"

    content = service.get_memory(guild_id, guild_name)
    assert f"# Server Memory: {guild_name}" in content
    assert "## Known Members" in content
    assert "## Server Facts & Lore" in content
    assert "## Recent Highlights" in content

    file_path = service.get_memory_path(guild_id)
    assert os.path.exists(file_path)
    with open(file_path, "r", encoding="utf-8") as f:
        saved = f.read()
    assert saved.strip() == content.strip()


def test_message_counter_and_interval(temp_memory_dir):
    service = MemoryService(base_dir=temp_memory_dir, update_interval=10)
    guild_id = 12345

    # First 9 messages should return False
    for i in range(9):
        triggered = service.on_message_received(guild_id)
        assert triggered is False
        assert service.get_message_count(guild_id) == i + 1

    # 10th message triggers consolidation and resets counter
    triggered = service.on_message_received(guild_id)
    assert triggered is True
    assert service.get_message_count(guild_id) == 0

    # 11th message starts from 1 again
    triggered = service.on_message_received(guild_id)
    assert triggered is False
    assert service.get_message_count(guild_id) == 1


def test_add_custom_memory(temp_memory_dir):
    service = MemoryService(base_dir=temp_memory_dir, update_interval=10)
    guild_id = 55555
    guild_name = "Takopi Fan Club"

    fact1 = "Yoshitaka is the server owner and creator of the bot."
    service.add_custom_memory(guild_id, fact1, guild_name)

    content = service.get_memory(guild_id, guild_name)
    assert f"- {fact1}" in content

    fact2 = "Takopi brings happiness and Happy Tools."
    service.add_custom_memory(guild_id, fact2, guild_name)

    updated_content = service.get_memory(guild_id, guild_name)
    assert f"- {fact1}" in updated_content
    assert f"- {fact2}" in updated_content


def test_clear_memory(temp_memory_dir):
    service = MemoryService(base_dir=temp_memory_dir, update_interval=10)
    guild_id = 77777
    guild_name = "Reset Guild"

    service.add_custom_memory(guild_id, "Temporary secret fact", guild_name)
    assert "Temporary secret fact" in service.get_memory(guild_id, guild_name)

    # Set counter
    for _ in range(5):
        service.on_message_received(guild_id)
    assert service.get_message_count(guild_id) == 5

    # Clear memory
    cleared = service.clear_memory(guild_id, guild_name)
    assert "Temporary secret fact" not in cleared
    assert "No custom facts recorded yet." in cleared
    assert service.get_message_count(guild_id) == 0


def test_memory_content_size_guard(temp_memory_dir):
    service = MemoryService(base_dir=temp_memory_dir, update_interval=10, max_chars=100)
    guild_id = 88888

    long_text = "A" * 500
    service.save_memory(guild_id, long_text)

    saved = service.get_memory(guild_id)
    assert len(saved) == 100


def test_gemini_server_memory_injection():
    with patch("google.generativeai.configure"):
        gemini = GeminiService(api_key="fake-key", system_prompt="Bot Base Persona")

        # Without server memory, uses base model
        model_plain = gemini._get_model(None)
        assert model_plain == gemini._model

        # With server memory, builds dynamic system instruction
        server_memory = "# Server Memory\n- Yoshitaka is owner"
        model_with_mem = gemini._get_model(server_memory)
        assert model_with_mem != gemini._model
        sys_text = model_with_mem._system_instruction.parts[0].text
        assert "Bot Base Persona" in sys_text
        assert "Server Memory" in sys_text
        assert "Yoshitaka is owner" in sys_text


@pytest.mark.asyncio
async def test_consolidate_memory(temp_memory_dir):
    service = MemoryService(base_dir=temp_memory_dir, update_interval=10)
    guild_id = 99999
    guild_name = "AI Lab"

    # Seed initial memory
    service.add_custom_memory(guild_id, "Project started in 2026", guild_name)

    mock_gemini = MagicMock()
    compacted_markdown = (
        "# Server Memory: AI Lab\n\n"
        "## Known Members\n"
        "- **yoshitaka**: Founder and lead engineer\n\n"
        "## Server Facts & Lore\n"
        "- Project started in 2026\n\n"
        "## Recent Highlights\n"
        "- Discussed server memory implementation\n"
    )
    mock_gemini.compact_memory_text = AsyncMock(return_value=compacted_markdown)

    recent_history = [
        {"role": "user", "content": "yoshitaka: We need to implement memory.md today"},
        {"role": "assistant", "content": "Sure! I will help design the memory architecture."},
    ]

    result = await service.consolidate_memory(
        guild_id=guild_id,
        guild_name=guild_name,
        gemini_service=mock_gemini,
        recent_messages=recent_history
    )

    assert "**yoshitaka**: Founder and lead engineer" in result
    assert "Discussed server memory implementation" in result
    mock_gemini.compact_memory_text.assert_awaited_once()

    # Verify saved to disk
    disk_content = service.get_memory(guild_id, guild_name)
    assert disk_content == compacted_markdown.strip()


@pytest.mark.asyncio
async def test_ai_responder_with_memory_service(temp_memory_dir):
    memory_service = MemoryService(base_dir=temp_memory_dir)
    guild_id = 11111
    guild_name = "Test Guild"
    memory_service.add_custom_memory(guild_id, "Yoshitaka loves cats", guild_name)

    mock_gemini = MagicMock()
    mock_gemini.max_len = 1900
    mock_gemini.ask_with_history = AsyncMock(return_value="Nyan!")

    history_mgr = ChatHistoryManager()
    mock_bot = MagicMock()
    mock_bot.user.name = "TakopiBot"

    responder = AIResponder(
        gemini=mock_gemini,
        history_manager=history_mgr,
        bot=mock_bot,
        memory_service=memory_service
    )

    mock_message = MagicMock()
    mock_message.guild.id = guild_id
    mock_message.guild.name = guild_name
    mock_message.author.display_name = "yoshitaka"
    mock_message.channel.name = "general"
    mock_message.content = "What pets do I like?"
    mock_message.attachments = []

    answer = await responder.get_answer(mock_message)
    assert answer == "Nyan!"

    # Verify server_memory was passed to ask_with_history
    mock_gemini.ask_with_history.assert_awaited_once()
    _, kwargs = mock_gemini.ask_with_history.call_args
    assert "server_memory" in kwargs
    assert "Yoshitaka loves cats" in kwargs["server_memory"]


@pytest.mark.asyncio
async def test_toggle_memory_command(temp_memory_dir):
    memory_service = MemoryService(base_dir=temp_memory_dir)
    mock_bot = MagicMock()
    mock_responder = MagicMock()
    mock_backup = MagicMock()

    cog = AICog(bot=mock_bot, responder=mock_responder, backup_service=mock_backup, memory_service=memory_service)
    assert cog.use_server_memory is True

    mock_interaction = MagicMock()
    mock_interaction.response.send_message = AsyncMock()

    # Toggle off
    await cog.toggle_memory.callback(cog, mock_interaction)
    assert cog.use_server_memory is False
    assert mock_responder.use_server_memory is False
    mock_interaction.response.send_message.assert_awaited_with("Server memory injection is now **disabled**.")

    # Toggle on
    await cog.toggle_memory.callback(cog, mock_interaction)
    assert cog.use_server_memory is True
    assert mock_responder.use_server_memory is True
    mock_interaction.response.send_message.assert_awaited_with("Server memory injection is now **enabled**.")

