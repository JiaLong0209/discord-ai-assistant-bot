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

## Speaker Styles

| スタイル | 繁體中文訳   |
| ---- | ------- |
| ノーマル | 一般／普通   |
| あまあま | 甜蜜／撒嬌   |
| ツンツン | 冷淡／高傲   |
| セクシー | 性感      |
| ささやき | 低語／耳語   |
| ヒソヒソ | 悄悄話／密語  |
| ヘロヘロ | 疲憊／軟弱   |
| なみだめ | 流淚／淚眼汪汪 |


## ALL Speaker IDs

| Name | Style | Speaker ID |
|----------|---------|------------|
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
