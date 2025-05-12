
import discord
from discord.ext import commands
from discord import app_commands

class ClearSlash(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True, aliases=['clearcommands'])
    async def clearslash(self, ctx):
        if ctx.author.id != 545609811354583040:
            return
        self.bot.tree.clear_commands(guild=None)
        await self.bot.tree.sync()
        await ctx.send("Cleared global slash commands.")

async def setup(bot):
    await bot.add_cog(ClearSlash(bot))
