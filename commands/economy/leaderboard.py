import discord
from discord.ext import commands
from discord import app_commands
from utils.database import db

class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Ranks users based on their networth (only top 10.)", aliases=['lb', 'top', 'rich'])
    async def leaderboard(self, ctx):
        await self._show_leaderboard(ctx)

    @app_commands.command(name="leaderboard", description="Ranks users based on their networth (only top 10.)")
    async def leaderboard_slash(self, interaction: discord.Interaction):
        await self._show_leaderboard(interaction)

    async def _show_leaderboard(self, ctx_or_interaction):
        guild_id = ctx_or_interaction.guild.id

        # Aggregate total money for each user in this guild
        pipeline = [
            {"$match": {"guild_id": str(guild_id)}},
            {"$addFields": {"total": {"$add": ["$pocket", "$bank"]}}},
            {"$sort": {"total": -1}},
            {"$limit": 10}
        ]

        user_totals = list(db.economies.aggregate(pipeline))

        embed = discord.Embed(
            title="🏆 Richest Users",
            color=discord.Color.gold()
        )

        for i, user_data in enumerate(user_totals, 1):
            try:
                user = await self.bot.fetch_user(int(user_data["user_id"]))
                embed.add_field(
                    name=f"{i}. {user.name}",
                    value=f"${user_data['total']:,}",
                    inline=False
                )
            except:
                continue

        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Leaderboard(bot))