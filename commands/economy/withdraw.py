
import discord
from discord.ext import commands
from discord import app_commands
from utils.database import get_balance, save_balance

class Withdraw(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Withdraw money from your bank.", aliases=['with', 'get'])
    async def withdraw(self, ctx, amount):
        await self._do_withdraw(ctx, amount)

    @app_commands.command(name="withdraw", description="Withdraw money from your bank")
    @app_commands.describe(amount="Amount to withdraw or 'all'")
    async def withdraw_slash(self, interaction: discord.Interaction, amount: str):
        await self._do_withdraw(interaction, amount)

    async def _do_withdraw(self, ctx_or_interaction, amount):
        try:
            user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
            guild_id = ctx_or_interaction.guild.id
            
            try:
                balance = get_balance(guild_id, user.id)
            except Exception as db_error:
                print(f"Database error in withdraw for user {user.id} in guild {guild_id}: {db_error}")
                error_embed = discord.Embed(
                    title="Database Error",
                    description="Could not connect to the database. Please try again later.",
                    color=discord.Color.red()
                )
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.response.send_message(embed=error_embed, ephemeral=True)
                else:
                    await ctx_or_interaction.send(embed=error_embed)
                return
        except Exception as e:
            print(f"Error in withdraw: {e}")
            error_embed = discord.Embed(
                title="Error",
                description="An unexpected error occurred. Please try again later.",
                color=discord.Color.red()
            )
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(embed=error_embed, ephemeral=True)
            else:
                await ctx_or_interaction.send(embed=error_embed)
            return

        if amount.lower() == "all":
            amount_to_withdraw = balance["bank"]
            if amount_to_withdraw == 0:
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.response.send_message("You have no money in your bank!")
                else:
                    await ctx_or_interaction.send("You have no money in your bank!")
                return
        else:
            try:
                amount_to_withdraw = int(amount)
            except ValueError:
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.response.send_message("Please provide a valid number or 'all'")
                else:
                    await ctx_or_interaction.send("Please provide a valid number or 'all'")
                return

        if amount_to_withdraw <= 0:
            embed = discord.Embed(
                title="Error",
                description="Amount must be positive!",
                color=discord.Color.red()
            )
        elif amount_to_withdraw > balance["bank"]:
            embed = discord.Embed(
                title="Error",
                description="You don't have that much money in your bank!",
                color=discord.Color.red()
            )
        else:
            balance["bank"] -= amount_to_withdraw
            balance["pocket"] += amount_to_withdraw
            save_balance(guild_id, user.id, balance)
            embed = discord.Embed(
                title="Withdrawal Successful",
                description=f"Withdrew ${amount_to_withdraw} from your bank!",
                color=discord.Color.green()
            )

        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Withdraw(bot))
