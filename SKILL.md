---
name: discord-ai-bot
description: >-
  Comprehensive architectural guidelines, design patterns, SOLID principles, and development runbook for the Discord AI Assistant Bot.
---

# Discord AI Assistant Bot - Developer & Architecture Skill

This document defines the architectural standards, design patterns, SOLID principles, and operational runbooks for maintaining and extending the Discord AI Assistant Bot.

---

## 1. Architectural Overview & Design Patterns

The codebase follows a modular, decoupled architecture adhering to the **SOLID principles**:

```mermaid
flowchart TD
    subgraph Core["Bot Core (DIP)"]
        Bot["AIBot (commands.Bot subclass)"]
        Settings["Settings (utils/config.py)"]
    end

    subgraph Providers["LLM Provider Strategy & Factory"]
        Base["BaseAIProvider (Interface)"]
        Gemini["GeminiProvider (Default)"]
        Factory["AIProviderFactory"]
        Factory --> Base
        Base <|-- Gemini
    end

    subgraph Helpers["Context & Adapters (Facade / Adapter)"]
        GC["GuildContext(id, name)"]
        Req["require_service()"]
        Adapter["InteractionAdapter (Message -> Interaction)"]
    end

    subgraph Services["Domain Services (SRP)"]
        Playback["VoicePlaybackService"]
        Memory["MemoryService"]
        History["ChatHistoryManager"]
        Backup["BackupService"]
        VoiceVox["VoiceVoxService"]
        Responder["AIResponder"]
    end

    subgraph Cogs["Modular Cogs (SRP)"]
        ChatCog["cogs/chat_cog.py"]
        VoiceCog["cogs/voice_cog.py"]
        VoiceVoxCog["cogs/voicevox_cog.py"]
        MemoryCog["cogs/memory_cog.py"]
        SettingsCog["cogs/settings_cog.py"]
    end

    Bot --> Providers
    Bot --> Services
    Cogs --> Helpers
    Cogs --> Services
```

### Applied Design Patterns

| Pattern | Implementation | Purpose |
| :--- | :--- | :--- |
| **Strategy & Factory** | [`services/providers/`](file:///data/Programming/discord-ai-assistant-bot/services/providers/) | Abstracts LLMs (`BaseAIProvider`). `AIProviderFactory` dynamically registers and instantiates providers (`gemini`, and future `openai`, `anthropic`, `ollama`). |
| **Facade** | [`utils/discord_context.py`](file:///data/Programming/discord-ai-assistant-bot/utils/discord_context.py) | `GuildContext` consolidates guild ID and name extraction. `require_service` provides a single guard function for service availability. |
| **Adapter** | [`utils/interaction_adapter.py`](file:///data/Programming/discord-ai-assistant-bot/utils/interaction_adapter.py) | `InteractionAdapter` wraps `discord.Message` into the `discord.Interaction` interface so `VoicePlaybackService` can process both uniformly. |
| **Service / Facade** | [`services/voice_playback.py`](file:///data/Programming/discord-ai-assistant-bot/services/voice_playback.py) | Encapsulates VoiceVox synthesis, WAV-to-MP3 compression, Discord voice streaming, cleanup callbacks, and followup responses. |
| **Dependency Inversion** | [`bot.py`](file:///data/Programming/discord-ai-assistant-bot/bot.py) | `AIBot(commands.Bot)` explicitly types all service dependencies instead of monkey-patching `bot` with `setattr`. |

---

## 2. Directory Structure

```text
├── bot.py                        # AIBot entrypoint, lifecycle, and cog loader
├── cogs/                         # Modular Discord Cogs (Single Responsibility)
│   ├── chat_cog.py               # /q, /ask, /imginfo, /fix_grammar, on_message
│   ├── voice_cog.py              # /voice_channel_join, /voice_channel_exit, /voice
│   ├── voicevox_cog.py           # VoiceVox parameters & configs
│   ├── memory_cog.py             # /memory group, /toggle_memory
│   ├── settings_cog.py           # Model switching, system prompt, toggles, /help
│   └── ai_cog.py                 # Backward-compatibility facade
├── services/                     # Domain business logic
│   ├── providers/                # Pluggable AI LLM Providers
│   │   ├── base.py               # BaseAIProvider abstract interface
│   │   ├── gemini_provider.py    # Google Gemini implementation
│   │   └── factory.py            # AIProviderFactory registry
│   ├── gemini.py                 # Re-exports GeminiProvider as GeminiService
│   ├── voice_playback.py         # TTS synthesis & voice channel streaming
│   ├── memory_service.py         # Server memory.md management & compaction
│   ├── chat_history.py           # Rolling in-memory chat history
│   ├── backup_service.py         # Audio (MP3) & Text backup service
│   ├── voicevox.py               # VoiceVox HTTP API client
│   └── voice_config.py           # VoiceVox configuration schemas
├── utils/                        # Utilities & Cross-cutting helpers
│   ├── discord_context.py        # GuildContext & require_service guard
│   ├── interaction_adapter.py    # Message -> Interaction adapter
│   ├── config.py                 # Settings dataclass & env loader
│   └── text.py                   # Regex text sanitizers
└── storage/                      # File persistence
    ├── memory/<guild_id>/        # Persistent per-server memory.md files
    └── backup/                   # Audio (MP3) & Text conversation archives
```

---

## 3. How to Extend: Adding a New AI Provider

To add another LLM provider (e.g. OpenAI, Anthropic, Ollama, Groq):

1. **Create `services/providers/openai_provider.py`**:
   ```python
   from services.providers.base import BaseAIProvider

   class OpenAIProvider(BaseAIProvider):
       def __init__(self, api_key: str, model_name: str = "gpt-4o", system_prompt: str = ""):
           self._model_name = model_name
           self._system_prompt = system_prompt
           # Initialize client...

       @property
       def provider_name(self) -> str:
           return "openai"

       # Implement all abstract methods from BaseAIProvider...
   ```

2. **Register in `AIProviderFactory`**:
   ```python
   from services.providers.factory import AIProviderFactory
   from services.providers.openai_provider import OpenAIProvider

   AIProviderFactory.register("openai", OpenAIProvider)
   ```

3. **Configure in `.env`**:
   ```bash
   AI_PROVIDER=openai
   OPENAI_API_KEY=sk-...
   ```
   No changes to Cogs, Responders, or Playback services are required (Open/Closed Principle).

---

## 4. Coding Conventions: Writing Slash Commands

When creating or editing Discord slash commands, **never repeat manual guild extraction or service checks**:

### Bad Practice (Anti-pattern):
```python
# AVOID THIS:
guild_id = interaction.guild_id or 0
guild_name = interaction.guild.name if interaction.guild else "Direct Message"
if not self.memory_service:
    await interaction.response.send_message("Memory service is not available.", ephemeral=True)
    return
```

### Good Practice (SOLID / Facade):
```python
# DO THIS:
from utils.discord_context import GuildContext, require_service

ctx = GuildContext.from_interaction(interaction)
if not await require_service(interaction, self.memory_service, "Memory service"):
    return

content = self.memory_service.get_memory(ctx.id, ctx.name)
```

---

## 5. Persistent Server Memory (`memory.md`) Rules

- **Storage**: `storage/memory/{guild_id}/memory.md` (or `storage/memory/dm/memory.md` for DMs).
- **Auto-Update**: Triggered every 10 messages in `cogs/chat_cog.py` via `asyncio.create_task` so chat replies are never blocked.
- **Compaction**: Uses LLM summarization to synthesize existing `memory.md` + recent 10 messages into structured sections:
  - `# Server Memory: <Guild Name>`
  - `## Known Members` (user roles, topics, interests)
  - `## Server Facts & Lore` (server rules, inside jokes)
  - `## Recent Highlights` (key events summary)
- **Token Budget**: Strictly clamped (`max_chars = 150000`), maintaining ~1K–3K tokens to preserve the 250K TPM limit.

---

## 6. Testing & Development Runbook

### Run Unit Tests
```bash
poetry run pytest -v
```

### Start Bot in Development
```bash
# Takopi Persona
ENV_FILE=.env.takopi USE_GUILD_SYNC=False poetry run python bot.py

# Shizuka Persona
ENV_FILE=.env.shizuka USE_GUILD_SYNC=False poetry run python bot.py
```

### Voice Channel DAVE Requirements
- Modern Discord voice channels enforce the DAVE end-to-end encryption protocol.
- Handled by `discord.py >= 2.7.1` + `davey >= 0.2.0`.
- All TTS backups are converted on-the-fly to MP3 via FFmpeg pipes to prevent disk exhaustion.

