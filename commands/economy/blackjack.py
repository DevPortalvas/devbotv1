import discord  
from discord.ext import commands  
from discord import app_commands  
import random  
import json  
import os  

DATA_FILE = "data.json"  

from utils.database import get_balance, update_balance

suits = ['♠', '♥', '♦', '♣']  
ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']  

def create_deck():  
    return [f"{rank}{suit}" for suit in suits for rank in ranks]  

def calculate_value(cards):  
    value = 0  
    aces = 0  
    for card in cards:  
        rank = card[:-1]  
        if rank in ['J', 'Q', 'K']:  
            value += 10  
        elif rank == 'A':  
            aces += 1  
            value += 11  
        else:  
            value += int(rank)  
    while value > 21 and aces:  
        value -= 10  
        aces -= 1  
    return value  

class BlackjackView(discord.ui.View):  
    def __init__(self, ctx_or_interaction, player_cards, dealer_cards, deck, bet):  
        super().__init__(timeout=60)  
        self.ctx_or_interaction = ctx_or_interaction  
        self.player_cards = player_cards  
        self.dealer_cards = dealer_cards  
        self.deck = deck  
        self.bet = bet  
        self.user_id = str(ctx_or_interaction.user.id if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author.id)  
        self.guild_id = str(ctx_or_interaction.guild.id if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.guild.id)
        self.user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author

    async def update_embed(self, interaction, result=None):  
        color = discord.Color.green()  
        if result and ("Dealer wins!" in result or "busted!" in result):  
            color = discord.Color.red()  
        embed = discord.Embed(title="Blackjack", color=color)  
        embed.add_field(name="Your Hand", value=f"{' '.join(self.player_cards)} ({calculate_value(self.player_cards)})", inline=False)  
        dealer_value = calculate_value(self.dealer_cards)  
        if result:  
            embed.add_field(name="Dealer's Hand", value=f"{' '.join(self.dealer_cards)} ({dealer_value})", inline=False)  
            embed.add_field(name="Result", value=result, inline=False)  
            self.clear_items()  
        else:  
            embed.add_field(name="Dealer's Hand", value=f"{self.dealer_cards[0]} ??", inline=False)  
        await interaction.response.edit_message(embed=embed, view=self)  

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.blurple)  
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):  
        if interaction.user.id == int(self.user_id):  
            self.player_cards.append(self.deck.pop())  
            if calculate_value(self.player_cards) > 21:  
                await self.update_embed(interaction, result="You busted! Dealer wins!")  
            else:  
                await self.update_embed(interaction)  

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.red)  
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):  
        if interaction.user.id == int(self.user_id):  
            while calculate_value(self.dealer_cards) < 17:  
                self.dealer_cards.append(self.deck.pop())  
            player_val = calculate_value(self.player_cards)  
            dealer_val = calculate_value(self.dealer_cards)  
            if dealer_val > 21:  
                result = "Dealer busted! You win!"  
                update_balance(interaction.guild.id, interaction.user.id, self.bet * 2, "pocket")  
            elif player_val > dealer_val:  
                result = "You win!"  
                update_balance(interaction.guild.id, interaction.user.id, self.bet * 2, "pocket")  
            elif player_val == dealer_val:  
                result = "It's a tie!"  
                update_balance(interaction.guild.id, interaction.user.id, self.bet, "pocket")  
            else:  
                result = "Dealer wins!"  
            await self.update_embed(interaction, result=result)  

    @discord.ui.button(label="Double Down", style=discord.ButtonStyle.green)  
    async def double_down(self, interaction: discord.Interaction, button: discord.ui.Button):  
        if interaction.user.id == int(self.user_id):  
            balance = get_balance(self.guild_id, self.user_id)  
            if balance['pocket'] < self.bet:  
                await interaction.response.send_message("You don't have enough money to double down!", ephemeral=True)  
                return  

            update_balance(interaction.guild.id, self.user_id, -self.bet, "pocket")  
            self.bet *= 2  
            self.player_cards.append(self.deck.pop())  
            player_val = calculate_value(self.player_cards)  

            while calculate_value(self.dealer_cards) < 17:  
                self.dealer_cards.append(self.deck.pop())  
            dealer_val = calculate_value(self.dealer_cards)  

            if player_val > 21:  
                result = "You busted! Dealer wins!"  
            elif dealer_val > 21:  
                result = "Dealer busted! You win!"  
                update_balance(interaction.guild.id, interaction.user.id, self.bet * 2, "pocket")  
            elif player_val > dealer_val:  
                result = "You win!"  
                update_balance(interaction.guild.id, interaction.user.id, self.bet * 2, "pocket")  
            elif player_val == dealer_val:  
                result = "It's a tie!"  
                update_balance(interaction.guild.id, interaction.user.id, self.bet, "pocket")  
            else:  
                result = "Dealer wins!"  

            await self.update_embed(interaction, result=result)  

class Blackjack(commands.Cog):  
    def __init__(self, bot):  
        self.bot = bot  

    @commands.command(help="BET URRRRR MONEYYYYY", aliases=['bj', '21'])
    @commands.cooldown(1, 5, commands.BucketType.member)  
    async def blackjack(self, ctx, bet):  
        await self._play_blackjack(ctx, bet)  

    @app_commands.command(name="blackjack", description="Play blackjack and bet your money")
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))  
    @app_commands.describe(bet="Amount to bet or 'all'")  
    async def blackjack_slash(self, interaction: discord.Interaction, bet: str):  
        await self._play_blackjack(interaction, bet)  

    async def _play_blackjack(self, ctx_or_interaction, bet):  
        user_id = str(ctx_or_interaction.user.id if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author.id)  
        guild_id = str(ctx_or_interaction.guild.id if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.guild.id)
        balance = get_balance(guild_id, user_id)  

        if bet.lower() == "all":  
            bet = balance['pocket']  
        else:  
            try:  
                bet = int(bet)  
            except ValueError:  
                if isinstance(ctx_or_interaction, discord.Interaction):  
                    await ctx_or_interaction.response.send_message("Please enter a valid number or 'all'")  
                else:  
                    await ctx_or_interaction.send("Please enter a valid number or 'all'")  
                return  

        if bet < 1000:  
            if isinstance(ctx_or_interaction, discord.Interaction):  
                await ctx_or_interaction.response.send_message("You must bet at least $1000.")  
            else:  
                await ctx_or_interaction.send("You must bet at least $1000.")  
            return  

        if balance['pocket'] < bet:  
            if isinstance(ctx_or_interaction, discord.Interaction):  
                await ctx_or_interaction.response.send_message("You don't have enough money to place that bet.")  
            else:  
                await ctx_or_interaction.send("You don't have enough money to place that bet.")  
            return  

        update_balance(guild_id, user_id, -bet, "pocket")
        deck = create_deck()  
        random.shuffle(deck)  
        player_cards = [deck.pop(), deck.pop()]  
        dealer_cards = [deck.pop(), deck.pop()]  
        view = BlackjackView(ctx_or_interaction, player_cards, dealer_cards, deck, bet)  

        embed = discord.Embed(title="Blackjack", color=discord.Color.green())  
        embed.add_field(name="Your Hand", value=f"{' '.join(player_cards)} ({calculate_value(player_cards)})", inline=False)  
        embed.add_field(name="Dealer's Hand", value=f"{dealer_cards[0]} ??", inline=False)  

        if isinstance(ctx_or_interaction, discord.Interaction):  
            await ctx_or_interaction.response.send_message(embed=embed, view=view)  
        else:  
            await ctx_or_interaction.send(embed=embed, view=view)

    @blackjack.error
    async def blackjack_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Please specify a bet amount!")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"Please wait {int(error.retry_after)} seconds before using this command again!")

    @blackjack_slash.error
    async def blackjack_slash_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(f"Please wait {int(error.retry_after)} seconds before using this command again!", ephemeral=True)

async def setup(bot):  
    await bot.add_cog(Blackjack(bot))