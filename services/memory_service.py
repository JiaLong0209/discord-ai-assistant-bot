from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime
import logging
import os
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class MemoryService:
    """Manages persistent per-server markdown memory (memory.md)."""

    def __init__(
        self,
        base_dir: str = "storage/memory",
        update_interval: int = 10,
        max_chars: int = 150000  # Hard safety cap well under 50K tokens
    ) -> None:
        self.base_dir = base_dir
        self.update_interval = update_interval
        self.max_chars = max_chars
        self._message_counters: Dict[int, int] = defaultdict(int)
        self._locks: Dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)
        os.makedirs(self.base_dir, exist_ok=True)

    def get_memory_path(self, guild_id: int) -> str:
        """Return the absolute or relative path to the server's memory.md file."""
        folder_name = str(guild_id) if guild_id else "dm"
        dir_path = os.path.join(self.base_dir, folder_name)
        os.makedirs(dir_path, exist_ok=True)
        return os.path.join(dir_path, "memory.md")

    def get_default_template(self, guild_name: str = "", guild_id: int = 0) -> str:
        """Generate default initial template for server memory."""
        name = guild_name.strip() or f"Guild {guild_id}" if guild_id else "Direct Message"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return (
            f"# Server Memory: {name}\n\n"
            f"- **Guild ID**: {guild_id}\n"
            f"- **Last Updated**: {now}\n\n"
            "## Known Members\n"
            "- No recorded members yet.\n\n"
            "## Server Facts & Lore\n"
            "- No custom facts recorded yet.\n\n"
            "## Recent Highlights\n"
            "- Memory initialized.\n"
        )

    def get_memory(self, guild_id: int, guild_name: str = "") -> str:
        """Read and return memory.md for the guild, creating the default template if missing."""
        path = self.get_memory_path(guild_id)
        if not os.path.exists(path):
            template = self.get_default_template(guild_name, guild_id)
            self.save_memory(guild_id, template)
            return template

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if not content:
                content = self.get_default_template(guild_name, guild_id)
                self.save_memory(guild_id, content)
            return content
        except Exception as e:
            logger.error("Failed to read memory file %s: %s", path, e)
            return self.get_default_template(guild_name, guild_id)

    def save_memory(self, guild_id: int, content: str) -> None:
        """Save memory content atomically, respecting the maximum character limit."""
        path = self.get_memory_path(guild_id)
        sanitized = (content or "").strip()
        if len(sanitized) > self.max_chars:
            logger.warning("Memory content exceeds max_chars (%d > %d), truncating", len(sanitized), self.max_chars)
            sanitized = sanitized[: self.max_chars]

        tmp_path = f"{path}.tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(sanitized + "\n")
            os.replace(tmp_path, path)
            logger.debug("Saved memory to %s (%d chars)", path, len(sanitized))
        except Exception as e:
            logger.error("Failed to write memory file %s: %s", path, e)
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    def on_message_received(self, guild_id: int) -> bool:
        """Increment message counter for guild. Return True if update threshold is reached."""
        self._message_counters[guild_id] += 1
        logger.debug("Guild %s message counter: %d/%d", guild_id, self._message_counters[guild_id], self.update_interval)
        if self._message_counters[guild_id] >= self.update_interval:
            self._message_counters[guild_id] = 0
            return True
        return False

    def get_message_count(self, guild_id: int) -> int:
        """Return the current message count towards the next auto-update."""
        return self._message_counters[guild_id]

    def add_custom_memory(self, guild_id: int, note: str, guild_name: str = "") -> str:
        """Append a custom fact/note under '## Server Facts & Lore'."""
        content = self.get_memory(guild_id, guild_name)
        bullet = f"- {note.strip()}"

        lore_pattern = r"(##\s*Server Facts & Lore\s*\n)"
        if re.search(lore_pattern, content, flags=re.IGNORECASE):
            # Replace placeholder if present
            if "- No custom facts recorded yet." in content:
                content = content.replace("- No custom facts recorded yet.", bullet)
            else:
                content = re.sub(
                    lore_pattern,
                    rf"\1{bullet}\n",
                    content,
                    count=1,
                    flags=re.IGNORECASE
                )
        else:
            content += f"\n\n## Server Facts & Lore\n{bullet}\n"

        self.save_memory(guild_id, content)
        return content

    def clear_memory(self, guild_id: int, guild_name: str = "") -> str:
        """Reset memory file to the default blank template and reset counter."""
        self._message_counters[guild_id] = 0
        template = self.get_default_template(guild_name, guild_id)
        self.save_memory(guild_id, template)
        return template

    async def consolidate_memory(
        self,
        guild_id: int,
        guild_name: str,
        gemini_service,
        recent_messages: List[dict]
    ) -> str:
        """Summarize and compact current memory.md with recent chat history using Gemini."""
        async with self._locks[guild_id]:
            current_memory = self.get_memory(guild_id, guild_name)
            if not recent_messages:
                return current_memory

            history_lines = []
            for msg in recent_messages:
                role = msg.get("role", "user")
                c = msg.get("content", "").strip()
                if c:
                    history_lines.append(f"[{role}]: {c}")

            recent_history_text = "\n".join(history_lines)
            logger.info("Consolidating memory for guild %s (%s) with %d recent messages", guild_id, guild_name, len(recent_messages))

            compacted = await gemini_service.compact_memory_text(
                current_memory=current_memory,
                recent_history_text=recent_history_text,
                guild_name=guild_name
            )

            if compacted and len(compacted.strip()) > 20:
                # Strip any accidental ```markdown wrapper
                cleaned = re.sub(r"^```(?:markdown|md)?\s*", "", compacted.strip(), flags=re.IGNORECASE)
                cleaned = re.sub(r"\s*```$", "", cleaned)
                self.save_memory(guild_id, cleaned)
                logger.info("Memory consolidated successfully for guild %s (length: %d chars)", guild_id, len(cleaned))
                return cleaned

            return current_memory

