
import discord
from discord.ext import commands
from discord import app_commands
from utils.database import db

class Prefix(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def has_permission(self, user: discord.Member):
        return (
            user.id == 545609811354583040 or
            user.guild_permissions.administrator or
            user.id == user.guild.owner_id
        )

    def get_prefix(self, guild_id: str):
        prefix_data = db.prefixes.find_one({"guild_id": str(guild_id)})
        return prefix_data["prefix"] if prefix_data else "?"

    @commands.command(help="Change the bot's prefix for this server")
    async def prefix(self, ctx, new_prefix: str = None):
        if not new_prefix:
            current = self.get_prefix(ctx.guild.id)
            await ctx.send(f"Current prefix is: `{current}`")
            return

        if not self.has_permission(ctx.author):
            await ctx.send("You don't have permission to change the prefix!")
            return

        db.prefixes.update_one(
            {"guild_id": str(ctx.guild.id)},
            {"$set": {"prefix": new_prefix}},
            upsert=True
        )
        await ctx.send(f"Prefix changed to: `{new_prefix}`")

async def setup(bot):
    await bot.add_cog(Prefix(bot))
