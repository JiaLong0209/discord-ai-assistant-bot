from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, TypeVar
import discord

T = TypeVar("T")


@dataclass(frozen=True)
class GuildContext:
    """Encapsulates normalized guild identifier and name from Discord interactions or messages."""

    id: int
    name: str

    @classmethod
    def from_interaction(cls, interaction: discord.Interaction) -> "GuildContext":
        """Extract GuildContext from a discord.Interaction."""
        return cls(
            id=interaction.guild_id or 0,
            name=interaction.guild.name if interaction.guild else "Direct Message"
        )

    @classmethod
    def from_message(cls, message: discord.Message) -> "GuildContext":
        """Extract GuildContext from a discord.Message."""
        return cls(
            id=message.guild.id if message.guild else 0,
            name=message.guild.name if message.guild else "Direct Message"
        )


async def require_service(
    interaction: discord.Interaction,
    service: Optional[T],
    service_name: str
) -> Optional[T]:
    """Ensure a service dependency is available, sending an ephemeral error message if missing.

    Returns the service if present, or None if missing.
    """
    if service is None:
        msg = f"⚠️ {service_name} is currently unavailable."
        if not interaction.response.is_done():
            await interaction.response.send_message(msg, ephemeral=True)
        else:
            await interaction.followup.send(msg, ephemeral=True)
        return None
    return service

