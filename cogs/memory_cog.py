from __future__ import annotations

import io
import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from services.memory_service import MemoryService
from services.ai_responder import AIResponder
from utils.discord_context import GuildContext, require_service

logger = logging.getLogger(__name__)


class MemoryCog(commands.Cog, name="Memory"):
    """Cog for managing persistent server memory (memory.md)."""

    def __init__(
        self,
        bot: commands.Bot,
        memory_service: Optional[MemoryService] = None,
        responder: Optional[AIResponder] = None
    ) -> None:
        self.bot = bot
        self.memory_service = memory_service
        self.responder = responder

    memory_group = app_commands.Group(name="memory", description="Manage persistent server memory (memory.md)")

    @memory_group.command(name="show", description="Show current server memory (memory.md).")
    async def memory_show(self, interaction: discord.Interaction) -> None:
        if not await require_service(interaction, self.memory_service, "Memory service"):
            return

        ctx = GuildContext.from_interaction(interaction)
        memory_content = self.memory_service.get_memory(ctx.id, ctx.name)

        if len(memory_content) <= 1800:
            await interaction.response.send_message(f"```markdown\n{memory_content}\n```", ephemeral=False)
        else:
            file = discord.File(io.BytesIO(memory_content.encode("utf-8")), filename="memory.md")
            summary = memory_content[:1500] + "\n\n*(Full memory attached below)*"
            await interaction.response.send_message(f"```markdown\n{summary}\n```", file=file, ephemeral=False)

    @memory_group.command(name="add", description="Add a note or fact to this server's memory.")
    async def memory_add(self, interaction: discord.Interaction, note: str) -> None:
        if not await require_service(interaction, self.memory_service, "Memory service"):
            return

        ctx = GuildContext.from_interaction(interaction)
        self.memory_service.add_custom_memory(ctx.id, note, ctx.name)
        await interaction.response.send_message(f"Added to server memory:\n> {note.strip()}")

    @memory_group.command(name="clear", description="Clear or reset this server's memory.md.")
    async def memory_clear(self, interaction: discord.Interaction) -> None:
        if not await require_service(interaction, self.memory_service, "Memory service"):
            return

        ctx = GuildContext.from_interaction(interaction)
        self.memory_service.clear_memory(ctx.id, ctx.name)
        await interaction.response.send_message(f"Server memory for **{ctx.name}** has been reset to defaults.")

    @memory_group.command(name="update", description="Consolidate and compact recent conversations into memory.md.")
    async def memory_update(self, interaction: discord.Interaction) -> None:
        if not await require_service(interaction, self.memory_service, "Memory service"):
            return
        if not await require_service(interaction, self.responder, "AI Responder"):
            return

        ctx = GuildContext.from_interaction(interaction)
        await interaction.response.defer(thinking=True)

        history = self.responder.history_manager.get_latest_history(ctx.id)
        if not history:
            await interaction.followup.send("No recent conversation history to consolidate.")
            return

        updated_memory = await self.memory_service.consolidate_memory(
            guild_id=ctx.id,
            guild_name=ctx.name,
            gemini_service=self.responder.gemini,
            recent_messages=history
        )

        if len(updated_memory) <= 1800:
            await interaction.followup.send(f"Memory updated and compacted:\n```markdown\n{updated_memory}\n```")
        else:
            file = discord.File(io.BytesIO(updated_memory.encode("utf-8")), filename="memory.md")
            summary = updated_memory[:1500] + "\n\n*(Full memory attached below)*"
            await interaction.followup.send(f"Memory updated and compacted:\n```markdown\n{summary}\n```", file=file)

    @app_commands.command(name="toggle_memory", description="Toggle whether AI uses persistent server memory (memory.md).")
    async def toggle_memory(self, interaction: discord.Interaction) -> None:
        if self.responder:
            self.responder.use_server_memory = not self.responder.use_server_memory
            status = "enabled" if self.responder.use_server_memory else "disabled"
        else:
            status = "unavailable"
        await interaction.response.send_message(f"Server memory injection is now **{status}**.")


async def setup(bot: commands.Bot) -> None:
    memory_service = getattr(bot, "memory_service", None)
    responder = getattr(bot, "ai_responder", None)
    await bot.add_cog(MemoryCog(bot=bot, memory_service=memory_service, responder=responder))

