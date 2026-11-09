from __future__ import annotations

from typing import Any
import discord


class MessageFollowupAdapter:
    """Adapter for interaction.followup when working with a discord.Message."""

    def __init__(self, message: discord.Message) -> None:
        self._message = message

    async def send(self, *args: Any, **kwargs: Any) -> discord.Message:
        return await self._message.channel.send(*args, **kwargs)


class InteractionAdapter:
    """Adapter Pattern: Adapts a discord.Message to the discord.Interaction interface.

    Allows commands and playback services designed for Interactions to handle Messages seamlessly.
    """

    def __init__(self, message: discord.Message) -> None:
        self.guild = message.guild
        self.guild_id = message.guild.id if message.guild else 0
        self.user = message.author
        self.channel = message.channel
        self.message = message
        self.followup = MessageFollowupAdapter(message)

    @classmethod
    def from_message(cls, message: discord.Message) -> "InteractionAdapter":
        return cls(message)

