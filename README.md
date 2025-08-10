# Discord AI Assistant Bot

This Discord bot integrates AI features including text Q&A, image description, grammar fixing, and voice synthesis with VoiceVox TTS and Gemini AI.

---

## Features & Commands

### `/q`  
Ask any question and get an AI-generated text answer.  
**Alias:** `/ask`

---

### `/imginfo`  
Upload an image (with optional text) and get an AI-generated description of the image.

---

### `/fix_grammar`  
Fix grammar, spelling, and phrasing of your input text.

---

### `/voice`  
Ask a question and get the answer spoken aloud using VoiceVox TTS audio.

---

### Voice Channel Controls

- **`/voice_channel_join [channel]`**  
Make the bot join your current voice channel or a specified voice channel.

- **`/voice_channel_exit`**  
Disconnect the bot from the current voice channel.

---

### VoiceVox Settings

- **`/change_speaker <speaker_id>`**  
Change the default VoiceVox speaker ID for voice synthesis.

---

### Gemini AI Settings

- **`/change_system_prompt <prompt>`**  
Change the system prompt that steers Gemini AI’s response style and persona.

---

## Usage

1. Use `/q` or `/ask` to interact with the AI via text.
2. Use `/voice` to get AI responses spoken with VoiceVox TTS in your voice channel.
3. Use `/voice_channel_join` to summon the bot into your voice channel.
4. Upload images with `/imginfo` to get AI-generated image descriptions.
5. Adjust voice and AI behavior with `/change_speaker` and `/change_system_prompt`.

---

## Requirements

- Discord bot token and permissions to use slash commands and join voice channels.
- VoiceVox TTS server running and accessible (for voice features).
- Gemini AI API configured for text generation and image description.

---

## Notes

- Voice channel commands require the bot to have permissions to connect and speak in voice channels.
- Changing the system prompt immediately affects how Gemini AI responds.
- VoiceVox speaker IDs depend on your local VoiceVox installation.

---

## Getting Started

### Prerequisites

- **Python 3.12.7**  
  Make sure you have Python 3.12.7 installed. You can check your version with:
  ```bash
  python --version
  ```

- **Poetry**  
  This project uses [Poetry](https://python-poetry.org/) for dependency management and virtual environments.

  To install Poetry, run:
  ```bash
  curl -sSL https://install.python-poetry.org | python3 -
  ```

  Or follow the [official installation guide](https://python-poetry.org/docs/#installation).

### Installation

1. **Clone the repository** (if you haven't already):
   ```bash
   git clone <your-repo-url>
   cd discord-ai-assistant-bot
   ```

2. **Install dependencies**:
   ```bash
   poetry install
   ```

3. **Activate the virtual environment**:
   ```bash
   poetry shell
   ```

4. **Run the bot**:
   ```bash
   python bot.py
   ```

---


## Using Voicevox TTS

If you want to use Voicevox TTS features, you **must install and run the VOICEVOX engine locally**.

1. **Download the VOICEVOX engine**  
   Visit the [VOICEVOX engine releases page](https://github.com/VOICEVOX/voicevox_engine/releases) and download the appropriate version for your OS.

2. **Extract and run the engine**  
   Follow the instructions in the [VOICEVOX engine README](https://github.com/VOICEVOX/voicevox_engine?tab=readme-ov-file#ユーザーガイド) to extract and start the engine on your computer.

3. **Keep the VOICEVOX engine running**  
   The bot will connect to the local VOICEVOX engine API for TTS features. Make sure the engine is running whenever you want to use TTS.

For more details and troubleshooting, see the [official VOICEVOX engine documentation](https://github.com/VOICEVOX/voicevox_engine?tab=readme-ov-file#ユーザーガイド).

---

**Note:**  
If you have multiple Python versions installed, you can tell Poetry to use Python 3.12.7 by running:
```bash
poetry env use 3.12.7
```
before `poetry install`.

For more information, see the [Poetry documentation](https://python-poetry.org/docs/).
---

Enjoy interacting with your AI-powered Discord assistant!  
Feel free to contribute or suggest new features.

