from __future__ import annotations
import re
import logging
import discord
from typing import Union
from utils.text import remove_time_tag
from .chat_history import ChatHistoryManager
from .gemini import GeminiService

logger = logging.getLogger(__name__)

class AIResponder:
    def __init__(self, gemini: GeminiService, history_manager: ChatHistoryManager, bot: discord.Client):
        self.gemini = gemini
        self.history_manager = history_manager
        self.bot = bot

    def _log_interaction(self, source: Union[discord.Message, discord.Interaction], question: str, answer: str = "", is_image: bool = False):
        guild_name = source.guild.name if source.guild else "DM"
        user_name = source.author.display_name if isinstance(source, discord.Message) else source.user.display_name
        channel_name = source.channel.name if hasattr(source.channel, "name") else "DM"
        prefix = "(image) " if is_image else ""
        logger.info(f"\n\n--------------------\n \
            [{guild_name}] [{channel_name}] [{self.history_manager._current_time()}] \n{user_name}: {prefix}{question}\nAI: {answer}")

    # TODO
    def _replace_mentions_with_names(self, message: discord.Message, content: str) -> str:
        def repl(match):
            user_id = int(match.group(1))
            user = message.guild.get_member(user_id) if message.guild else None
            # return user.display_name if user else f"<@{user_id}>"
            return user.display_name if user else f""
        return re.sub(r"<@!?(\d+)>", repl, content)

    async def get_answer(self, source: Union[discord.Message, discord.Interaction], question: str) -> str:
        guild_id = source.guild.id if source.guild else 0
        user_name = source.author.display_name if isinstance(source, discord.Message) else source.user.display_name

        if isinstance(source, discord.Message):
            question = self._replace_mentions_with_names(source, question)

        history = self.history_manager.get_latest_history(guild_id)
        bot_name = self.bot.user.name

        attachments = source.attachments if isinstance(source, discord.Message) else []
        if attachments:
            for attachment in attachments:
                if attachment.content_type and attachment.content_type.startswith("image/"):
                    image_bytes = await attachment.read()
                    history_text = "\n".join(f"{h['role']}: {h['content']}" for h in history)
                    combined_prompt = f"{history_text}\n{user_name}: {question}"
                    self.history_manager.add_user_message(guild_id, user_name, f"[sent image] {question}")
                    answer = await self.gemini.describe_image(image_bytes, mime_type=attachment.content_type, text=combined_prompt)
                    answer = remove_time_tag(answer)
                    self.history_manager.add_assistant_message(guild_id, bot_name, answer)
                    self._log_interaction(source, question, answer, is_image=True)
                    return answer

        self.history_manager.add_user_message(guild_id, user_name, question)
        answer = await self.gemini.ask_with_history(history, f"{user_name}: {question}")
        answer = remove_time_tag(answer)
        self.history_manager.add_assistant_message(guild_id, bot_name, answer)
        self._log_interaction(source, question, answer)
        return answer

