
import discord
from discord.ext import commands
from discord import app_commands
import random

class RussianRoulette(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}  # Store active games

    @commands.command(name="russianroulette", aliases=['rr', 'russian'])
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def russianroulette(self, ctx, opponent: discord.Member):
        await self._start_game(ctx, opponent)

    @app_commands.command(name="russianroulette", description="Play Russian Roulette with another user")
    @app_commands.describe(opponent="The user to challenge")
    @app_commands.checks.cooldown(1, 30, key=lambda i: (i.guild_id, i.user.id))
    async def russianroulette_slash(self, interaction: discord.Interaction, opponent: discord.Member):
        await self._start_game(interaction, opponent)

    async def _start_game(self, ctx_or_interaction, opponent):
        if isinstance(ctx_or_interaction, discord.Interaction):
            user = ctx_or_interaction.user
            channel = ctx_or_interaction.channel
        else:
            user = ctx_or_interaction.author
            channel = ctx_or_interaction.channel

        if opponent.bot or opponent == user:
            msg = "You can't play against bots or yourself!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        # Randomly decide who goes first
        players = [user, opponent]
        current_player = random.choice(players)
        other_player = opponent if current_player == user else user

        # Initialize game state
        game_state = {
            "total_rounds": 8,
            "remaining_rounds": 8,
            "shell_position": random.randint(1, 8),
            "current_player": current_player,
            "other_player": other_player
        }

        self.active_games[channel.id] = game_state

        # Create the button
        class TriggerButton(discord.ui.Button):
            def __init__(self, cog, channel):
                super().__init__(style=discord.ButtonStyle.grey, label="Trigger")
                self.cog = cog
                self.channel = channel

            async def callback(self, interaction: discord.Interaction):
                if interaction.user != game_state["current_player"]:
                    await interaction.response.send_message("It's not your turn!", ephemeral=True)
                    return

                # Calculate probability of shooting opponent
                shoot_opponent = random.random() < 0.49  # 15% chance
                hit_chance = 1 / game_state["remaining_rounds"]
                got_shot = random.random() < hit_chance

                game_state["remaining_rounds"] -= 1

                if got_shot:
                    loser = game_state["other_player"] if shoot_opponent else game_state["current_player"]
                    winner = game_state["current_player"] if shoot_opponent else game_state["other_player"]
                    
                    result_embed = discord.Embed(
                        title="🔫 BANG!",
                        description=f"💀 {loser.mention} got shot!\n🏆 {winner.mention} wins!",
                        color=discord.Color.red()
                    )
                    await interaction.message.edit(embed=result_embed, view=None)
                    await interaction.response.defer()
                    del self.cog.active_games[self.channel.id]
                    return

                # Switch players
                game_state["current_player"], game_state["other_player"] = game_state["other_player"], game_state["current_player"]

                # Update embed
                new_embed = discord.Embed(
                    title="🔫 Russian Roulette",
                    description=f"It's {game_state['current_player'].mention}'s turn!\n"
                               f"Rounds remaining: {game_state['remaining_rounds']}\n"
                               f"Chance of getting shot: {(1/game_state['remaining_rounds']*100):.1f}%",
                    color=discord.Color.gold()
                )
                await interaction.message.edit(embed=new_embed)
                await interaction.response.defer()

        # Create the view and add the button
        view = discord.ui.View()
        view.add_item(TriggerButton(self, channel))

        # Create initial embed
        embed = discord.Embed(
            title="🔫 Russian Roulette",
            description=f"It's {current_player.mention}'s turn!\n"
                       f"Rounds remaining: {game_state['remaining_rounds']}\n"
                       f"Chance of getting shot: 12.5%",
            color=discord.Color.gold()
        )

        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embed, view=view)
        else:
            await ctx_or_interaction.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(RussianRoulette(bot))
