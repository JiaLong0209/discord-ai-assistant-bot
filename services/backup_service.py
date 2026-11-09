from __future__ import annotations
import os
import subprocess
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class BackupService:
    def __init__(self, base_dir="storage/backup"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _make_timestamp(self):
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def backup_audio(self, wav_bytes: bytes, speaker_id: int, guild_id: int, timestamp=None) -> str:
        timestamp = timestamp or self._make_timestamp()
        dir_path = os.path.join(self.base_dir, "audio", str(speaker_id))
        os.makedirs(dir_path, exist_ok=True)

        # Convert WAV bytes to MP3 via ffmpeg pipe to save disk space
        try:
            cmd = ["ffmpeg", "-y", "-i", "pipe:0", "-f", "mp3", "-b:a", "128k", "pipe:1"]
            proc = subprocess.run(cmd, input=wav_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            mp3_bytes = proc.stdout
            path = os.path.join(dir_path, f"{guild_id}_{timestamp}.mp3")
            data_to_write = mp3_bytes
        except Exception as e:
            logger.warning("Failed to convert audio to mp3, falling back to wav: %s", e)
            path = os.path.join(dir_path, f"{guild_id}_{timestamp}.wav")
            data_to_write = wav_bytes

        with open(path, "wb") as f:
            f.write(data_to_write)
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
