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
from .message_preprocessor import MessagePreprocessor

logger = logging.getLogger(__name__)

class AttachmentHandler:
    """Handles extraction of relevant attachments (images, etc.)"""


class AIResponder:
    def __init__(self, gemini: GeminiService, history_manager: ChatHistoryManager, bot: discord.Client):
        self.gemini = gemini
        self.history_manager = history_manager
        self.bot = bot

    def _log_interaction(self, source, question, answer="", is_image=False):
        guild_name = source.guild.name if source.guild else "DM"
        user_name = source.author.display_name if isinstance(source, discord.Message) else source.user.display_name
        channel_name = source.channel.name if hasattr(source.channel, "name") else "DM"
        prefix = "(image) " if is_image else ""
        logger.info(
            f"\n\n--------------------\n"
            f"[{guild_name}] [{channel_name}] [{self.history_manager._current_time()}] \n"
            f"{user_name}: {prefix}{question}\nAI: {answer}"
        )

    async def get_answer(self, source: Union[discord.Message, discord.Interaction], add_to_history: bool = True) -> str:
        guild_id = source.guild.id if source.guild else 0
        user_name = source.author.display_name if isinstance(source, discord.Message) else source.user.display_name
        bot_name = self.bot.user.name

        # Preprocess text
        if isinstance(source, discord.Message):
            question = MessagePreprocessor.normalize(source)
        else:
            question = source.data.get("content", "")

        history = self.history_manager.get_latest_history(guild_id)

        # Check for images (own + reply)
        if isinstance(source, discord.Message):
            images = MessagePreprocessor.collect_images(source)
        else:
            images = []

        if images:
            # → Step1: describe each image
            descriptions = []
            logger.info(f"Total images: {len(images)}")
            for i, image in  enumerate(images):
                image_bytes = await image.read()
                desc = await self.gemini.describe_image(
                    image_bytes, mime_type=image.content_type
                )
                logger.info(f"Image ({i+1}) description: {desc}")
                desc = remove_time_tag(desc)
                descriptions.append(desc)

            # → Step2: combine description into new prompt
            image_context = " ".join(f"[Image ({i+1}) description: {d}]" for i, d in enumerate(descriptions))
            combined_prompt = f"{image_context}\n{user_name}: {question}"
            logging.info(f"combined_prompt: {combined_prompt}")
            answer = await self.gemini.ask_with_history(history, combined_prompt)

            if add_to_history:
                self.history_manager.add_user_message(guild_id, user_name, f"[sent image] {question}")
                self.history_manager.add_assistant_message(guild_id, bot_name, answer)

            self._log_interaction(source, question, answer, is_image=True)
            return answer

        # Normal text
        answer = await self.gemini.ask_with_history(history, f"{user_name}: {question}")
        answer = remove_time_tag(answer)

        if add_to_history:
            self.history_manager.add_user_message(guild_id, user_name, question)
            self.history_manager.add_assistant_message(guild_id, bot_name, answer)

        self._log_interaction(source, question, answer)
        return answer