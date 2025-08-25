from __future__ import annotations
from email import message
from imaplib import Commands
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

    def format_message_with_reply(self, message: discord.Message) -> str:
        """Format message content, including reply context if present."""
        content = message.content or ""

        # もし返信があれば追加情報をつける
        if message.reference and message.reference.resolved:
            replied_msg: discord.Message = message.reference.resolved
            replied_author = replied_msg.author.display_name
            replied_content = replied_msg.content or ""

            # Handle image references in the replied message
            image_refs = []
            for attach in replied_msg.attachments:
                if attach.content_type and attach.content_type.startswith("image/"):
                    image_refs.append(f"[Image: {attach.url}]")

            if image_refs:
                replied_content = f"{replied_content} {' '.join(image_refs)}".strip()

            # 返信部分を先頭に追加
            content = f"[reply: {replied_author}: {replied_content}] {content}"

        return content.strip()


    def _replace_mentions_with_names(self, message: discord.Message, content: str) -> str:
        mention_map = {m.id: m.display_name for m in message.mentions}

        def repl(match):
            user_id = int(match.group(1))
            user_name = mention_map.get(user_id)
            return f"@{user_name}" if user_name else f"<@{user_id}>"

        return re.sub(r"<@&?(\d+)>", repl, content)

    def normalize_question_text(self, message: discord.Message):
        question = self.format_message_with_reply(message)
        question = self._replace_mentions_with_names(message, question)


        return question

    async def get_answer(self, source: Union[discord.Message, discord.Interaction], question: str, add_to_history: bool = True) -> str:
        guild_id = source.guild.id if source.guild else 0
        user_name = source.author.display_name if isinstance(source, discord.Message) else source.user.display_name

        history = self.history_manager.get_latest_history(guild_id)
        bot_name = self.bot.user.name
        

        attachments = source.attachments if isinstance(source, discord.Message) else []
        if attachments:
            for attachment in attachments:
                if attachment.content_type and attachment.content_type.startswith("image/"):
                    
                    image_bytes = await attachment.read()
                    history_text = "\n".join(f"{h['role']}: {h['content']}" for h in history)
                    combined_prompt = f"{history_text}\n{user_name}: {question}"
                    answer = await self.gemini.describe_image(image_bytes, mime_type=attachment.content_type, text=combined_prompt)
                    answer = remove_time_tag(answer)

                    self.history_manager.add_user_message(guild_id, user_name, f"[sent image] {question}")
                    self.history_manager.add_assistant_message(guild_id, bot_name, answer)

                    self._log_interaction(source, question, answer, is_image=True)
                    return answer

        answer = await self.gemini.ask_with_history(history, f"{user_name}: {question}")
        answer = remove_time_tag(answer)

        if add_to_history:
            self.history_manager.add_user_message(guild_id, user_name, question)
            self.history_manager.add_assistant_message(guild_id, bot_name, answer)

        self._log_interaction(source, question, answer)
        return answer

