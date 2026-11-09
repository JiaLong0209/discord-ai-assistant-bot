<div align="center">

# Discord AI Assistant Bot

**An intelligent, multi-modal Discord bot featuring Google Gemini AI, VoiceVox Neural TTS, Discord DAVE E2EE Voice Streaming, and Persistent Per-Server Long-Term Memory.**

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![discord.py](https://img.shields.io/badge/discord.py-v2.7.1%20(Voice%20%2B%20DAVE)-5865F2.svg?logo=discord&logoColor=white)](https://github.com/Rapptz/discord.py)
[![VOICEVOX](https://img.shields.io/badge/VOICEVOX-Neural%20TTS-A0D8EF.svg)](https://voicevox.hiroshiba.jp/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## 📖 Table of Contents
- [✨ Key Highlights](#-key-highlights)
- [💻 Command Reference](#-command-reference)
  - [🤖 AI Chat & Multimodal](#-ai-chat--multimodal)
  - [🔊 Voice Channel & Spoken Replies](#-voice-channel--spoken-replies)
  - [🧠 Persistent Server Memory](#-persistent-server-memory)
  - [🎙️ VOICEVOX TTS Configuration](#️-voicevox-tts-configuration)
  - [⚙️ Bot & Session Management](#️-bot--session-management)
- [🚀 Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Configuration](#environment-configuration)
  - [Running VOICEVOX Engine](#running-voicevox-engine)
  - [Starting the Bot](#starting-the-bot)
- [🏗️ Architecture & Design Patterns](#️-architecture--design-patterns)
- [🎭 VOICEVOX Speaker Reference](#-voicevox-speaker-reference)
- [📄 License](#-license)

---

## ✨ Key Highlights

- 🧠 **Persistent Server Memory (`memory.md`)**:
  - Each Discord server maintains an isolated Markdown memory file (`storage/memory/<guild_id>/memory.md`).
  - **10-Message Auto-Compaction**: Automatically triggers an asynchronous background LLM summarization every 10 messages, discarding trivial chatter while preserving known member profiles, roles, and server lore.
  - **Dynamic System Instruction**: Injects the server's long-term memory directly into the AI's hidden persona prompt without polluting user chat history.
  - Strictly token-budgeted (< 50K tokens) to preserve Gemini's 250K TPM limits.

- 🎙️ **Voice Channel Playback with Discord DAVE E2EE**:
  - Full support for Discord's modern End-to-End Encryption (**DAVE protocol**) using `discord.py >= 2.7.1` and `davey`.
  - Seamless speech synthesis in voice channels using local **VOICEVOX** neural TTS models.
  - Real-time **WAV-to-MP3 streaming conversion** via FFmpeg pipes to save 90%+ storage on audio archives.

- 🔌 **Pluggable Multi-Model AI Provider Architecture**:
  - Implements the **Strategy and Factory design patterns** (`BaseAIProvider`, `GeminiProvider`, `AIProviderFactory`).
  - Easily extendable to OpenAI, Anthropic, or local Ollama models in the future without modifying core business logic.

- 💬 **Multimodal Conversational Capabilities**:
  - Text Q&A with rolling conversational memory.
  - Visual understanding via `/imginfo` for image analysis and descriptions.
  - Grammar and tone editor via `/fix_grammar` supporting Japanese, Traditional Chinese, and English.

- 🧱 **SOLID & Modular Codebase**:
  - Decoupled into specialized Cogs (`ChatCog`, `VoiceCog`, `VoiceVoxCog`, `MemoryCog`, `SettingsCog`).
  - Encapsulated Discord context helpers (`GuildContext`) and service prerequisite guards (`require_service`).

---

## 💻 Command Reference

### 🤖 AI Chat & Multimodal

| Command | Arguments | Description |
| :--- | :--- | :--- |
| `/q` *(alias: `/ask`)* | `text: str` | Ask the AI any question and receive a context-aware text response. |
| `/imginfo` | `image: Attachment`, `[text: str]` | Upload an image for multimodal analysis and optional prompt guidance. |
| `/fix_grammar` | `text: str` | Check and rewrite text with natural phrasing, grammar correction, and spelling fixes. |

---

### 🔊 Voice Channel & Spoken Replies

| Command | Arguments | Description |
| :--- | :--- | :--- |
| `/voice` | `text: str` | Ask a question and receive both a text answer and spoken VOICEVOX audio. |
| `/voice_channel_join` | `[channel: VoiceChannel]` | Connect the bot to your current voice channel or a specified voice channel. |
| `/voice_channel_exit` | *None* | Disconnect the bot from the active voice channel. |

---

### 🧠 Persistent Server Memory

| Command | Arguments | Description |
| :--- | :--- | :--- |
| `/memory show` | *None* | Display the server's current `memory.md` (attaches file if > 1,800 characters). |
| `/memory add` | `note: str` | Add a custom fact, rule, or piece of lore under `## Server Facts & Lore`. |
| `/memory clear` | *None* | Reset the server's `memory.md` to a clean default template. |
| `/memory update` | *None* | Manually trigger immediate AI compaction of recent conversations into memory. |
| `/toggle_memory` | *None* | Toggle whether persistent server memory is injected into AI prompts for this guild. |

---

### 🎙️ VOICEVOX TTS Configuration

| Command | Arguments | Description |
| :--- | :--- | :--- |
| `/change_speaker` | `speaker_id: int` | Switch the active VOICEVOX speaker ID (e.g., Zundamon, Shikoku Metan). |
| `/reset_speaker` | *None* | Reset the speaker ID back to the `.env` default. |
| `/change_speed_scale` | `speed: float` | Adjust speech playback speed (e.g. `1.0`, `1.2`). |
| `/change_pitch_scale` | `pitch: float` | Adjust voice pitch. |
| `/change_intonation_scale` | `scale: float` | Adjust speech intonation. |
| `/change_volume_scale` | `volume: float` | Adjust speech audio volume. |
| `/change_pause_length_scale`| `scale: float` | Adjust pause duration between punctuation marks. |
| `/show_config` | *None* | View the current VOICEVOX audio parameter settings. |
| `/reset_config` | *None* | Reset all VOICEVOX parameters back to defaults. |

---

### ⚙️ Bot & Session Management

| Command | Arguments | Description |
| :--- | :--- | :--- |
| `/change_gemini_model` | `model: Choice` | Dynamically switch the active Gemini/Gemma AI model from a live list. |
| `/change_system_prompt` | `prompt: str` | Change the AI's persona or system instructions in real-time. |
| `/reset_system_prompt` | *None* | Reset the system prompt back to the file template defined in `.env`. |
| `/set_history_length` | `length: int (1-50)`| Adjust the rolling conversation context window size. |
| `/clear_history` | *None* | Clear the server's in-memory conversation history. |
| `/reset_all` | *None* | Reset history, persona, and VOICEVOX configs to original defaults. |
| `/toggle_mention` | *None* | Toggle whether the AI mentions users in replies. |
| `/toggle_listen` | *None* | Toggle reply to all server messages vs. mentions only. |
| `/toggle_backup_audio` | *None* | Toggle automatic MP3 audio backup archiving. |
| `/toggle_backup_text` | *None* | Toggle text response archiving. |
| `/help` | *None* | Display a comprehensive, categorized Discord embed of all commands. |

---

## 🚀 Getting Started

### Prerequisites

- **Python**: `3.12.7` or newer
- **Poetry**: Package and dependency management
- **FFmpeg**: Required on the host system for Discord audio streaming and MP3 encoding
- **Discord Bot Token**: With `Message Content Intent` and Voice permissions enabled in the [Discord Developer Portal](https://discord.com/developers/applications)
- **Google Gemini API Key**: Obtainable from [Google AI Studio](https://aistudio.google.com/)

---

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/discord-ai-assistant-bot.git
   cd discord-ai-assistant-bot
   ```

2. **Configure Poetry environment**:
   ```bash
   poetry env use 3.12.7
   poetry install
   ```

---

### Environment Configuration

Copy the template file to create your environment configuration:
```bash
cp .env_template .env
```

| Variable | Required | Default | Description |
| :--- | :---: | :--- | :--- |
| `DISCORD_BOT_TOKEN` | **Yes** | — | Bot token from Discord Developer Portal. |
| `GOOGLE_API_KEY` | **Yes** | — | Google Gemini API key. |
| `GUILD_ID` | Optional | — | Specific guild ID for instant slash command synchronization. |
| `USE_GUILD_SYNC` | Optional | `false` | Set `true` to immediately sync commands to `GUILD_ID` (instant vs global 1hr propagation). |
| `GEMINI_MODEL` | Optional | `gemini-3.1-flash-lite` | Active model identifier. |
| `SYSTEM_PROMPT_DIR` | Optional | `sys_prompts` | Directory containing persona prompt files. |
| `SYSTEM_PROMPT_FILENAME` | Optional | `takopi.txt` | Prompt file to load on startup (e.g. `takopi.txt`, `kuze_shizuka.txt`). |
| `VOICEVOX_HOST` | Optional | `http://127.0.0.1:50021` | Base URL of your local or remote VOICEVOX engine. |
| `VOICEVOX_SPEAKER` | Optional | `1` | Default speaker ID. |
| `LATEST_N_HISTORY` | Optional | `10` | Context history window length. |
| `MEMORY_DIR` | Optional | `storage/memory` | Directory where per-server `memory.md` files are stored. |
| `MEMORY_UPDATE_INTERVAL` | Optional | `10` | Number of messages between automatic memory compactions. |
| `BACKUP_DIR` | Optional | `storage/backup` | Directory where audio (MP3) and text logs are saved. |

---

### Running VOICEVOX Engine

For speech synthesis, the VOICEVOX engine must be running locally:

1. Download the engine for your platform from the [VOICEVOX Releases page](https://github.com/VOICEVOX/voicevox_engine/releases).
2. Start the engine (e.g. on Linux with NVIDIA GPU):
   ```bash
   ./voicevox/linux-nvidia/run --use_gpu
   ```
   *The engine will listen on `http://127.0.0.1:50021` by default.*

---

### Starting the Bot

Start the bot using Poetry with your preferred persona configuration:

```bash
# Run with Takopi persona
ENV_FILE=.env.takopi USE_GUILD_SYNC=False poetry run python bot.py

# Or run with Shizuka persona
ENV_FILE=.env.shizuka USE_GUILD_SYNC=False poetry run python bot.py
```

To run tests:
```bash
poetry run pytest -v
```

---

## 🏗️ Architecture & Design Patterns

The codebase is built around **SOLID Principles** and documented in detail in [`SKILL.md`](./SKILL.md):

```text
├── bot.py                        # Strongly-typed AIBot(commands.Bot) & extension loader
├── cogs/                         # Modular Discord Cogs (SRP)
│   ├── chat_cog.py               # AI Chat, Image info, Grammar fix, Message listener
│   ├── voice_cog.py              # Voice channel connection & spoken replies
│   ├── voicevox_cog.py           # VoiceVox audio parameter configurations
│   ├── memory_cog.py             # Server persistent memory.md commands
│   ├── settings_cog.py           # Model switching, persona prompts, /help
│   └── ai_cog.py                 # Backward-compatibility facade
├── services/                     # Domain Logic Layer
│   ├── providers/                # Strategy & Factory Pattern for LLM providers
│   │   ├── base.py               # BaseAIProvider abstract interface
│   │   ├── gemini_provider.py    # Google Gemini provider
│   │   └── factory.py            # AIProviderFactory registry
│   ├── voice_playback.py         # VoicePlaybackService (Synthesis + E2EE Voice Stream)
│   ├── memory_service.py         # MemoryService (storage/memory/<guild_id>/memory.md)
│   ├── chat_history.py           # In-memory rolling conversation history
│   ├── backup_service.py         # BackupService (Realtime MP3 compression)
│   └── voicevox.py               # VoiceVox HTTP API client
└── utils/                        # Context & Adapter Helpers
    ├── discord_context.py        # GuildContext value object & require_service guard
    ├── interaction_adapter.py    # Message -> Interaction adapter
    └── config.py                 # Strongly-typed Settings dataclass
```

---

## 🎭 VOICEVOX Speaker Reference

### Popular Speaker Styles

| Style | Traditional Chinese Translation | English Meaning |
| :--- | :--- | :--- |
| **ノーマル** | 一般／普通 | Normal |
| **あまあま** | 甜蜜／撒嬌 | Sweet |
| **ツンツン** | 冷淡／高傲 | Tsundere |
| **セクシー** | 性感 | Sexy |
| **ささやき** | 低語／耳語 | Whisper |
| **ヒソヒソ** | 悄悄話／密語 | Secretive |
| **ヘロヘロ** | 疲憊／軟弱 | Exhausted |
| **なみだめ** | 流淚／淚眼汪汪 | Tearful |

<details>
<summary><b>Click to expand full list of 100+ VOICEVOX Speaker IDs</b></summary>

| Name | Style | Speaker ID |
| :--- | :--- | :---: |
| 四国めたん | ノーマル | 2 |
| 四国めたん | あまあま | 0 |
| 四国めたん | ツンツン | 6 |
| 四国めたん | セクシー | 4 |
| 四国めたん | ささやき | 36 |
| 四国めたん | ヒソヒソ | 37 |
| ずんだもん | ノーマル | 3 |
| ずんだもん | あまあま | 1 |
| ずんだもん | ツンツン | 7 |
| ずんだもん | セクシー | 5 |
| ずんだもん | ささやき | 22 |
| ずんだもん | ヒソヒソ | 38 |
| ずんだもん | ヘロヘロ | 75 |
| ずんだもん | なみだめ | 76 |
| 春日部つむぎ | ノーマル | 8 |
| 雨晴はう | ノーマル | 10 |
| 波音リツ | ノーマル | 9 |
| 波音リツ | クイーン | 65 |
| 玄野武宏 | ノーマル | 11 |
| 玄野武宏 | 喜び | 39 |
| 玄野武宏 | ツンギレ | 40 |
| 玄野武宏 | 悲しみ | 41 |
| 白上虎太郎 | ふつう | 12 |
| 白上虎太郎 | わーい | 32 |
| 白上虎太郎 | びくびく | 33 |
| 白上虎太郎 | おこ | 34 |
| 白上虎太郎 | びえーん | 35 |
| 青山龍星 | ノーマル | 13 |
| 青山龍星 | 熱血 | 81 |
| 青山龍星 | 不機嫌 | 82 |
| 青山龍星 | 喜び | 83 |
| 青山龍星 | しっとり | 84 |
| 青山龍星 | かなしみ | 85 |
| 青山龍星 | 囁き | 86 |
| 冥鳴ひまり | ノーマル | 14 |
| 九州そら | ノーマル | 16 |
| 九州そら | あまあま | 15 |
| 九州そら | ツンツン | 18 |
| 九州そら | セクシー | 17 |
| 九州そら | ささやき | 19 |
| もち子さん | ノーマル | 20 |
| もち子さん | セクシー／あん子 | 66 |
| もち子さん | 泣き | 77 |
| もち子さん | 怒り | 78 |
| もち子さん | 喜び | 79 |
| もち子さん | のんびり | 80 |
| 剣崎雌雄 | ノーマル | 21 |
| WhiteCUL | ノーマル | 23 |
| WhiteCUL | たのしい | 24 |
| WhiteCUL | かなしい | 25 |
| WhiteCUL | びえーん | 26 |
| 後鬼 | 人間ver. | 27 |
| 後鬼 | ぬいぐるみver. | 28 |
| 後鬼 | 人間（怒り）ver. | 87 |
| 後鬼 | 鬼ver. | 88 |
| No.7 | ノーマル | 29 |
| No.7 | アナウンス | 30 |
| No.7 | 読み聞かせ | 31 |
| ちび式じい | ノーマル | 42 |
| 櫻歌ミコ | ノーマル | 43 |
| 櫻歌ミコ | 第二形態 | 44 |
| 櫻歌ミコ | ロリ | 45 |
| 小夜/SAYO | ノーマル | 46 |
| ナースロボ＿タイプＴ | ノーマル | 47 |
| ナースロボ＿タイプＴ | 楽々 | 48 |
| ナースロボ＿タイプＴ | 恐怖 | 49 |
| ナースロボ＿タイプＴ | 内緒話 | 50 |
| †聖騎士 紅桜† | ノーマル | 51 |
| 雀松朱司 | ノーマル | 52 |
| 麒ヶ島宗麟 | ノーマル | 53 |
| 春歌ナナ | ノーマル | 54 |
| 猫使アル | ノーマル | 55 |
| 猫使アル | おちつき | 56 |
| 猫使アル | うきうき | 57 |
| 猫使アル | つよつよ | 110 |
| 猫使アル | へろへろ | 111 |
| 猫使ビィ | ノーマル | 58 |
| 猫使ビィ | おちつき | 59 |
| 猫使ビィ | 人見知り | 60 |
| 猫使ビィ | つよつよ | 112 |
| 中国うさぎ | ノーマル | 61 |
| 中国うさぎ | おどろき | 62 |
| 中国うさぎ | こわがり | 63 |
| 中国うさぎ | へろへろ | 64 |
| 栗田まろん | ノーマル | 67 |
| あいえるたん | ノーマル | 68 |
| 満別花丸 | ノーマル | 69 |
| 満別花丸 | 元気 | 70 |
| 満別花丸 | ささやき | 71 |
| 満別花丸 | ぶりっ子 | 72 |
| 満別花丸 | ボーイ | 73 |
| 琴詠ニア | ノーマル | 74 |
| Voidoll | ノーマル | 89 |
| ぞん子 | ノーマル | 90 |
| ぞん子 | 低血圧 | 91 |
| ぞん子 | 覚醒 | 92 |
| ぞん子 | 実況風 | 93 |
| 中部つるぎ | ノーマル | 94 |
| 中部つるぎ | 怒り | 95 |
| 中部つるぎ | ヒソヒソ | 96 |
| 中部つるぎ | おどおど | 97 |
| 中部つるぎ | 絶望と敗北 | 98 |
| 離途 | ノーマル | 99 |
| 離途 | シリアス | 101 |
| 黒沢冴白 | ノーマル | 100 |
| ユーレイちゃん | ノーマル | 102 |
| ユーレイちゃん | 甘々 | 103 |
| ユーレイちゃん | 哀しみ | 104 |
| ユーレイちゃん | ささやき | 105 |
| ユーレイちゃん | ツクモちゃん | 106 |
| 東北ずん子 | ノーマル | 107 |
| 東北きりたん | ノーマル | 108 |
| 東北イタコ | ノーマル | 109 |

</details>

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
