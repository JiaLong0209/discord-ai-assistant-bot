from __future__ import annotations
from datetime import datetime
from typing import DefaultDict, List
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class ChatHistoryManager:
    def __init__(self, latest_n: int = 10):
        self.latest_n = latest_n
        self._history: DefaultDict[int, List[dict]] = defaultdict(list)

    def _current_time(self) -> str:
        return datetime.now().strftime("%Y/%m/%d %H:%M:%S")

    def add_user_message(self, guild_id: int, user_name: str, content: str):
        timestamp = self._current_time()
        self._history[guild_id].append({
            "role": "user",
            "content": f"[time: {timestamp}] {user_name}: {content}"
        })
        self._trim_history(guild_id)

    def add_assistant_message(self, guild_id: int, bot_name: str, content: str):
        timestamp = self._current_time()
        self._history[guild_id].append({
            "role": "assistant",
            "content": f"[time: {timestamp}] {content}",
        })
        self._trim_history(guild_id)

    def _trim_history(self, guild_id: int):
        if len(self._history[guild_id]) > self.latest_n * 2:
            self._history[guild_id] = self._history[guild_id][-self.latest_n*2:]

    def get_latest_history(self, guild_id: int) -> List[dict]:
        logger.info(f"Latest history: {self._history[guild_id][-self.latest_n*2:]}")
        return self._history[guild_id][-self.latest_n*2:]

