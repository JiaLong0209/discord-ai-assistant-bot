import os
import wave
import struct
import tempfile
import pytest
from services.backup_service import BackupService

def create_dummy_wav() -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = f.name
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        # 0.5s of silence
        data = struct.pack("<" + "h" * 12000, *([0] * 12000))
        wf.writeframes(data)
    with open(path, "rb") as f:
        content = f.read()
    os.unlink(path)
    return content

def test_backup_audio_saves_mp3(tmp_path):
    service = BackupService(base_dir=str(tmp_path))
    wav_bytes = create_dummy_wav()
    saved_path = service.backup_audio(wav_bytes, speaker_id=3, guild_id=123)
    
    assert saved_path.endswith(".mp3")
    assert os.path.exists(saved_path)
    assert os.path.getsize(saved_path) > 0
    # MP3 should be significantly smaller than raw WAV
    assert os.path.getsize(saved_path) < len(wav_bytes)

