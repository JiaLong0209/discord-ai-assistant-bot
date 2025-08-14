from __future__ import annotations
import os
from datetime import datetime

class BackupService:
    def __init__(self, base_dir="storage/backup"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _make_timestamp(self):
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def backup_audio(self, wav_bytes: bytes, speaker_id: int, guild_id: int, timestamp=None):
        timestamp = timestamp or self._make_timestamp()
        dir_path = os.path.join(self.base_dir, "audio", str(speaker_id))
        os.makedirs(dir_path, exist_ok=True)
        path = os.path.join(dir_path, f"{guild_id}_{timestamp}.wav")
        with open(path, "wb") as f:
            f.write(wav_bytes)
        return path

    def backup_text(self, text: str, speaker_id: int, guild_id: int, timestamp=None):
        timestamp = timestamp or self._make_timestamp()
        dir_path = os.path.join(self.base_dir, "text", str(speaker_id))
        os.makedirs(dir_path, exist_ok=True)
        path = os.path.join(dir_path, f"{guild_id}_{timestamp}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def backup_all(self, wav_bytes: bytes, text: str, speaker_id: int, guild_id: int):
        timestamp = self._make_timestamp()
        audio_path = self.backup_audio(wav_bytes, speaker_id, guild_id, timestamp)
        text_path = self.backup_text(text, speaker_id, guild_id, timestamp)
        return audio_path, text_path
