
import discord
from discord.ext import commands
from discord import app_commands

class Ping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Shows the bot's latency")
    async def ping(self, ctx):
        await self._show_ping(ctx)

    @app_commands.command(name="ping", description="Shows the bot's latency")
    async def ping_slash(self, interaction: discord.Interaction):
        await self._show_ping(interaction)

    async def _show_ping(self, ctx_or_interaction):
        latency = round(self.bot.latency * 1000)
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"Bot latency: {latency}ms",
            color=discord.Color.green()
        )

        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Ping(bot))
