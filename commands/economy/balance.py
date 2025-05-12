
import discord
from discord.ext import commands
from discord import app_commands
from utils.database import get_balance

class Balance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Check your current money in your pocket and your bank.", aliases=['bal', 'money', 'wallet'])
    async def balance(self, ctx, member: discord.Member=None):
        await self._check_balance(ctx, member)

    @app_commands.command(name="balance", description="Check your current money in your pocket and your bank")
    async def balance_slash(self, interaction: discord.Interaction, member: discord.Member=None):
        await self._check_balance(interaction, member)

    async def _check_balance(self, ctx_or_interaction, member=None):
        try:
            user = member or (ctx_or_interaction.author if hasattr(ctx_or_interaction, 'author') else ctx_or_interaction.user)
            guild_id = ctx_or_interaction.guild.id
            
            try:
                bal = get_balance(guild_id, user.id)
            except Exception as db_error:
                print(f"Database error for user {user.id} in guild {guild_id}: {db_error}")
                error_embed = discord.Embed(
                    title="Database Error",
                    description="Could not connect to the database. Please try again later.",
                    color=discord.Color.red()
                )
                if isinstance(ctx_or_interaction, discord.Interaction):
                    if ctx_or_interaction.response.is_done():
                        await ctx_or_interaction.followup.send(embed=error_embed)
                    else:
                        await ctx_or_interaction.response.send_message(embed=error_embed)
                else:
                    await ctx_or_interaction.send(embed=error_embed)
                return

            embed = discord.Embed(title=f"{user.name}'s Balance", color=discord.Color.green())
            pocket_display = "∞" if bal.get('pocket', 0) >= 2**63-1 else f"${bal.get('pocket', 0):,}"
            bank_display = "∞" if bal.get('bank', 0) >= 2**63-1 else f"${bal.get('bank', 0):,}"
            bank_limit = bal.get('bank_limit', 10000)
            bank_limit_display = "∞" if bank_limit >= 2**63-1 else f"${bank_limit:,}"
            
            embed.add_field(name="Pocket", value=pocket_display, inline=True)
            embed.add_field(name="Bank", value=f"{bank_display} / {bank_limit_display}", inline=True)

            if isinstance(ctx_or_interaction, discord.Interaction):
                if not ctx_or_interaction.response.is_done():
                    await ctx_or_interaction.response.send_message(embed=embed)
                else:
                    await ctx_or_interaction.followup.send(embed=embed)
            else:
                await ctx_or_interaction.send(embed=embed)
                
        except Exception as e:
            print(f"General error in balance command: {e}")
            error_embed = discord.Embed(
                title="Error",
                description="An unexpected error occurred. Please try again later.",
                color=discord.Color.red()
            )
            if isinstance(ctx_or_interaction, discord.Interaction):
                if ctx_or_interaction.response.is_done():
                    await ctx_or_interaction.followup.send(embed=error_embed)
                else:
                    await ctx_or_interaction.response.send_message(embed=error_embed)
            else:
                await ctx_or_interaction.send(embed=error_embed)

async def setup(bot):
    await bot.add_cog(Balance(bot))
