# services/voice_config.py
import json
from copy import deepcopy
from enum import Enum

class VoiceVoxConfigKey(Enum):
    SPEED_SCALE = "speedScale"
    PITCH_SCALE = "pitchScale"
    INTONATION_SCALE = "intonationScale"
    VOLUME_SCALE = "volumeScale"
    PAUSE_LENGTH_SCALE = "pauseLengthScale"
    PAUSE_LENGTH = "pauseLength"
    PRE_PHONEME_LENGTH = "prePhonemeLength"
    POST_PHONEME_LENGTH = "postPhonemeLength"
    OUTPUT_SAMPLING_RATE = "outputSamplingRate"
    OUTPUT_STEREO = "outputStereo"

class VoiceVoxConfig:
    DEFAULTS = {
        VoiceVoxConfigKey.SPEED_SCALE.value: 1.0,
        VoiceVoxConfigKey.PITCH_SCALE.value: 0,
        VoiceVoxConfigKey.INTONATION_SCALE.value: 1.0,
        VoiceVoxConfigKey.VOLUME_SCALE.value: 1.5,
        VoiceVoxConfigKey.PRE_PHONEME_LENGTH.value: 0.1,
        VoiceVoxConfigKey.POST_PHONEME_LENGTH.value: 0.1,
        VoiceVoxConfigKey.PAUSE_LENGTH.value: None,
        VoiceVoxConfigKey.PAUSE_LENGTH_SCALE.value: 0.9,
        VoiceVoxConfigKey.OUTPUT_SAMPLING_RATE.value: 44100,
        VoiceVoxConfigKey.OUTPUT_STEREO.value: True,
    }

    def __init__(self, config=None):
        self._config = deepcopy(self.DEFAULTS)
        if config:
            self._config.update(config)

    def set(self, key, value):
        if isinstance(key, VoiceVoxConfigKey):
            key = key.value
        if key not in self.DEFAULTS:
            raise KeyError(f"Invalid config key: {key}")
        self._config[key] = value

    def get(self, key):
        if isinstance(key, VoiceVoxConfigKey):
            key = key.value
        return self._config.get(key)

    def reset(self):
        self._config = deepcopy(self.DEFAULTS)

    def as_dict(self):
        return deepcopy(self._config)

    def apply_to_query(self, query_data: dict) -> dict:
        updated = deepcopy(query_data)
        for key, val in self._config.items():
            if val is not None and key in updated:
                updated[key] = val
        return updated

    @classmethod
    def load(cls, path="voicevox_config.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls(data)
        except FileNotFoundError:
            # If not found, create with defaults and save
            config = cls()
            config.save(path)
            return config

    def save(self, path="voicevox_config.json"):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)
