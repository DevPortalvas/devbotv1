import discord
from discord.ext import commands
from discord import app_commands
import random
from utils.database import update_balance

class Work(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Work for money, cooldown = 10 minutes.", aliases=['w'])
    @commands.cooldown(1, 600, commands.BucketType.member)
    async def work(self, ctx):
        await self.do_work_prefix(ctx)

    @app_commands.command(name="work", description="Work for money (10 min cooldown)")
    @app_commands.checks.cooldown(1, 600, key=lambda i: (i.guild_id, i.user.id))
    async def work_slash(self, interaction: discord.Interaction):
        await self.do_work_slash(interaction)

    async def do_work_prefix(self, ctx):
        try:
            earnings = random.randint(1000, 5000)
            try:
                update_balance(ctx.guild.id, ctx.author.id, earnings)
            except Exception as db_error:
                print(f"Database error in work for user {ctx.author.id} in guild {ctx.guild.id}: {db_error}")
                error_embed = discord.Embed(
                    title="Database Error",
                    description="Could not connect to the database. Please try again later.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=error_embed)
                return
            msg = f"You worked hard and earned ${earnings}!"
            embed = discord.Embed(title="You finally did a job pig!", description=msg, color=discord.Color.orange())
            await ctx.send(embed=embed)
        except Exception as e:
            print(f"Error in work: {e}")
            await ctx.send("An error occurred while processing your request.")

    async def do_work_slash(self, interaction: discord.Interaction):
        earnings = random.randint(1000, 5000)
        update_balance(interaction.guild.id, interaction.user.id, earnings)
        msg = f"You worked hard and earned ${earnings}!"
        embed = discord.Embed(title="You finally did a job pig!", description=msg, color=discord.Color.orange())
        await interaction.response.send_message(embed=embed)

    @work.error
    async def work_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(
                title="You're tired!",
                description=f"Come back in {int(error.retry_after // 60)} minutes.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @work_slash.error
    async def work_slash_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            embed = discord.Embed(
                title="You're tired!",
                description=f"Come back in {int(error.retry_after // 60)} minutes.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Work(bot))