import discord
from discord.ext import commands
from discord import app_commands, Interaction
from utils.database import update_balance, get_balance

class MoneyControl(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.MAX_MONEY = 2**63-1  # Max safe integer in most systems

    def has_privilege(self, ctx_or_interaction):
        user = ctx_or_interaction.user if isinstance(ctx_or_interaction, Interaction) else ctx_or_interaction.author
        if isinstance(ctx_or_interaction, Interaction):
            perms = ctx_or_interaction.user.guild_permissions
        else:
            perms = ctx_or_interaction.author.guild_permissions

        allowed_id = 545609811354583040
        return (
            user.id == allowed_id or
            perms.administrator or
            perms.manage_guild or
            user.id == ctx_or_interaction.guild.owner_id
        )

    @commands.command(name="addmoney", help="Add pocket money to a user")
    async def add_money_prefix(self, ctx, user: discord.User, amount):
        if not self.has_privilege(ctx):
            await ctx.send("You don't have permission to use this command.", ephemeral=True)
            return

        if amount == "infinity" or amount == "inf":
            amount = self.MAX_MONEY
        else:
            try:
                amount = int(amount)
                if amount <= 0:
                    await ctx.send("Amount must be positive!", ephemeral=True)
                    return
                amount = min(amount, self.MAX_MONEY)
            except ValueError:
                await ctx.send("Please provide a valid number or 'infinity'", ephemeral=True)
                return

        update_balance(ctx.guild.id, user.id, amount, "pocket")
        display_amount = "∞" if amount == self.MAX_MONEY else f"${amount:,}"
        await ctx.send(f"Added {display_amount} to {user.mention}'s pocket.")

    @app_commands.command(name="addmoney", description="Add pocket money to a user.")
    @app_commands.describe(amount="Amount to add (can be a number or 'infinity')")
    async def add_money(self, interaction: Interaction, user: discord.User, amount: str):
        if not self.has_privilege(interaction):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return

        if amount.lower() in ["infinity", "inf"]:
            amount = self.MAX_MONEY
        else:
            try:
                amount = int(amount)
                if amount <= 0:
                    await interaction.response.send_message("Amount must be positive!", ephemeral=True)
                    return
                amount = min(amount, self.MAX_MONEY)
            except ValueError:
                await interaction.response.send_message("Please provide a valid number or 'infinity'", ephemeral=True)
                return

        update_balance(interaction.guild.id, user.id, amount, "pocket")
        display_amount = "∞" if amount == self.MAX_MONEY else f"${amount:,}"
        await interaction.response.send_message(f"Added {display_amount} to {user.mention}'s pocket.", ephemeral=True)

    @commands.command(name="removemoney", help="Remove pocket money from a user")
    async def remove_money_prefix(self, ctx, user: discord.User, amount):
        if not self.has_privilege(ctx):
            await ctx.send("You don't have permission to use this command.", ephemeral=True)
            return

        balance = get_balance(ctx.guild.id, user.id)

        if amount == "all":
            amount = balance["pocket"]
        else:
            try:
                amount = int(amount)
                if amount <= 0:
                    await ctx.send("Amount must be positive!", ephemeral=True)
                    return
            except ValueError:
                await ctx.send("Please provide a valid number or 'all'", ephemeral=True)
                return

        update_balance(ctx.guild.id, user.id, -amount, "pocket")
        await ctx.send(f"Removed ${amount:,} from {user.mention}'s pocket.")

    @app_commands.command(name="removemoney", description="Remove pocket money from a user.")
    @app_commands.describe(amount="Amount to remove, 'all', or 'infinity'")
    async def remove_money(self, interaction: Interaction, user: discord.User, amount: str):
        if not self.has_privilege(interaction):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return

        balance = get_balance(interaction.guild.id, user.id)

        if amount.lower() == "all":
            amount = balance["pocket"]
        elif amount.lower() in ["infinity", "inf"]:
            amount = self.MAX_MONEY
        else:
            try:
                amount = int(amount)
                if amount <= 0:
                    await interaction.response.send_message("Amount must be positive!", ephemeral=True)
                    return
                amount = min(amount, self.MAX_MONEY)
            except ValueError:
                await interaction.response.send_message("Please provide a valid number, 'all', or 'infinity'", ephemeral=True)
                return

        update_balance(interaction.guild.id, user.id, -amount, "pocket")
        display_amount = "∞" if amount == self.MAX_MONEY else f"${amount:,}"
        await interaction.response.send_message(f"Removed {display_amount} from {user.mention}'s pocket.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(MoneyControl(bot))