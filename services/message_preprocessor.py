import re
import discord
from typing import List


class MessagePreprocessor:
    """Utility to normalize questions for AIResponder."""

    @staticmethod
    def format_with_reply(message: discord.Message) -> str:
        """Format message content, including reply context if present."""
        content = message.content or ""

        if message.reference and message.reference.resolved:
            replied_msg: discord.Message = message.reference.resolved
            replied_author = replied_msg.author.display_name
            replied_content = replied_msg.content or ""

            # Add reply images
            image_refs = MessagePreprocessor._extract_image_refs(replied_msg.attachments)
            if image_refs:
                replied_content = f"{replied_content} {' '.join(image_refs)}".strip()

            content = f"[reply: {replied_author}: {replied_content}] {content}"

        return content.strip()

    @staticmethod
    def _extract_image_refs(attachments: List[discord.Attachment]) -> List[str]:
        """Return markdown-style references for image attachments."""
        refs = []
        for attach in attachments:
            if attach.content_type and attach.content_type.startswith("image/"):
                refs.append(f" [Image] ")
        return refs

    @staticmethod
    def replace_mentions(message: discord.Message, content: str) -> str:
        """Replace user mentions with display names."""
        mention_map = {m.id: m.display_name for m in message.mentions}

        def repl(match):
            user_id = int(match.group(1))
            user_name = mention_map.get(user_id)
            return f"@{user_name}" if user_name else f"<@{user_id}>"

        return re.sub(r"<@&?(\d+)>", repl, content)

    @classmethod
    def normalize(cls, message: discord.Message) -> str:
        """Prepare question text (reply context + mentions)."""
        question = cls.format_with_reply(message)
        return cls.replace_mentions(message, question)

    @staticmethod
    def collect_images(message: discord.Message) -> list[discord.Attachment]:
        attachments = list(message.attachments)
        if message.reference and isinstance(message.reference.resolved, discord.Message):
            attachments.extend(message.reference.resolved.attachments)
        return [a for a in attachments if a.content_type and a.content_type.startswith("image/")]

