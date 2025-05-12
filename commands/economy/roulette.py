
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random

ROULETTE_OPTIONS = ["Red", "Black", "Green"] + [str(i) for i in range(37)]
WIN_MULTIPLIERS = {
    "Red": 2,
    "Black": 2,
    "Green": 14,
    **{str(i): 35 for i in range(37)}  # 35x payout for direct number hits
}

RED_NUMBERS = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
BLACK_NUMBERS = [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]

from utils.database import get_balance, update_balance

active_game = {
    "message_id": None,
    "bets": {},
    "participants": set(),
    "status": "idle"
}

class ColorSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Red", description="Bet on Red (2x)", emoji="🔴"),
            discord.SelectOption(label="Black", description="Bet on Black (2x)", emoji="⚫"),
            discord.SelectOption(label="Green", description="Bet on Green (14x)", emoji="🟢")
        ]
        super().__init__(placeholder="Choose color to bet on...", min_values=0, max_values=3, options=options)

class NumberSelect(discord.ui.Select):
    def __init__(self, start, end):
        options = []
        for i in range(start, end + 1):
            color = "🔴" if i in RED_NUMBERS else "⚫" if i in BLACK_NUMBERS else "🟢"
            options.append(discord.SelectOption(label=str(i), description=f"Bet on {i} (35x)", emoji=color))
        super().__init__(placeholder=f"Choose numbers {start}-{end}...", min_values=0, max_values=len(options), options=options)

class BetView(discord.ui.View):
    def __init__(self, bot, bet_amount):
        super().__init__(timeout=180)
        self.bot = bot
        self.bet_amount = bet_amount
        self.selected_bets = set()
        
        # Add select menus
        self.add_item(ColorSelect())
        self.add_item(NumberSelect(0, 12))
        self.add_item(NumberSelect(13, 24))
        self.add_item(NumberSelect(25, 36))

        for item in self.children:
            item.callback = self.select_callback

    async def select_callback(self, interaction: discord.Interaction):
        self.selected_bets.clear()
        for item in self.children:
            if item.values:
                self.selected_bets.update(item.values)
        
        if not self.selected_bets:
            await interaction.response.send_message("Please select at least one bet option.", ephemeral=True)
            return

        user = interaction.user
        user_id = str(user.id)
        guild_id = interaction.guild.id
        bal = get_balance(guild_id, user_id)

        if bal["pocket"] < self.bet_amount:
            await interaction.response.send_message("You don't have enough money.", ephemeral=True)
            return

        split_amount = self.bet_amount // len(self.selected_bets)
        if split_amount == 0:
            await interaction.response.send_message("Your bet is too small to split.", ephemeral=True)
            return

        update_balance(guild_id, user.id, -self.bet_amount, "pocket")
        active_game["bets"][user_id] = {"amount": self.bet_amount, "choices": list(self.selected_bets)}
        active_game["participants"].add(interaction.user)

        await interaction.response.send_message(
            f"Your bet of ${self.bet_amount} was split across: {', '.join(self.selected_bets)}", ephemeral=True
        )

class Roulette(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['spin', 'bet'])
    @commands.cooldown(1, 5, commands.BucketType.member)
    async def roulette(self, ctx, bet: str):
        await self.start_roulette(ctx, bet)

    @app_commands.command(name="roulette", description="Bet on a roulette spin (use 'all' to bet everything)")
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.describe(bet="Amount to bet or type 'all'")
    async def roulette_slash(self, interaction: discord.Interaction, bet: str):
        await self.start_roulette(interaction, bet)

    async def start_roulette(self, ctx_or_interaction, bet):
        user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
        user_id = str(user.id)
        guild_id = ctx_or_interaction.guild.id if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.guild.id
        balance = get_balance(str(guild_id), str(user_id))

        if bet.lower() == "all":
            bet_amount = balance["pocket"]
        elif bet.isdigit():
            bet_amount = int(bet)
        else:
            await self._send(ctx_or_interaction, "Invalid bet. Use a number or 'all'.", True)
            return

        if bet_amount <= 0 or bet_amount > balance["pocket"]:
            await self._send(ctx_or_interaction, "Insufficient pocket balance.", True)
            return

        if active_game["status"] == "active":
            await self.join_existing_game(ctx_or_interaction, bet_amount)
            return

        active_game["bets"].clear()
        active_game["participants"].clear()
        active_game["status"] = "active"

        embed = discord.Embed(title="Roulette Started", description="Select your bets from the menus below.", color=discord.Color.blurple())
        embed.set_footer(text="Others can join for 20 seconds.")

        view = BetView(self.bot, bet_amount)
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embed, view=view)
            sent = await ctx_or_interaction.original_response()
        else:
            sent = await ctx_or_interaction.send(embed=embed, view=view)

        active_game["message_id"] = sent.id
        await asyncio.sleep(20)
        await self.run_roulette(sent.channel)

    async def join_existing_game(self, ctx_or_interaction, bet_amount):
        embed = discord.Embed(title="Join Roulette", description="You joined the current round. Pick your bets:", color=discord.Color.blurple())
        view = BetView(self.bot, bet_amount)
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        else:
            await ctx_or_interaction.send(embed=embed, view=view)

    async def run_roulette(self, channel):
        result_number = random.randint(0, 36)
        if result_number in RED_NUMBERS:
            result = ["Red", str(result_number)]
        elif result_number in BLACK_NUMBERS:
            result = ["Black", str(result_number)]
        else:
            result = ["Green", str(result_number)]

        winners = []
        for user_id, info in active_game["bets"].items():
            user = self.bot.get_user(int(user_id))
            guild = channel.guild
            
            winning_choices = [choice for choice in info["choices"] if choice in result]
            if winning_choices:
                share = info["amount"] // len(info["choices"])
                total_winnings = 0
                for choice in winning_choices:
                    winnings = share * WIN_MULTIPLIERS[choice]
                    total_winnings += winnings
                
                if total_winnings > 0:
                    update_balance(str(guild.id), str(user.id), total_winnings, "pocket")
                    winners.append(f"<@{user_id}> won ${total_winnings}")

        result_embed = discord.Embed(
            title="Roulette Result", 
            description=f"The ball landed on **{result_number}** ({result[0]})!", 
            color=discord.Color.green()
        )
        
        if winners:
            result_embed.add_field(name="Winners", value="\n".join(winners), inline=False)
        else:
            result_embed.add_field(name="No Winners", value="Better luck next time!", inline=False)

        await channel.send(embed=result_embed)
        active_game["status"] = "idle"

    async def _send(self, ctx_or_interaction, content, ephemeral=False):
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(content, ephemeral=ephemeral)
        else:
            await ctx_or_interaction.send(content)

async def setup(bot):
    await bot.add_cog(Roulette(bot))
