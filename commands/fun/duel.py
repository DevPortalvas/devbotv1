
import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio

class Duel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_duels = {}

    @commands.command(name="duel", aliases=['fight', 'challenge'])
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def duel(self, ctx, opponent: discord.Member):
        await self._start_duel(ctx, opponent)

    @app_commands.command(name="duel", description="Challenge someone to a medieval duel")
    @app_commands.describe(opponent="The user to challenge")
    async def duel_slash(self, interaction: discord.Interaction, opponent: discord.Member):
        await self._start_duel(interaction, opponent)

    def create_health_bar(self, health):
        bar_length = 20
        filled = int((health / 100) * bar_length)
        return f"[{'█' * filled}{'░' * (bar_length - filled)}] {health}HP"

    def get_action_message(self, action, attacker, defender, damage=0, blocked=0):
        messages = {
            "slash": [
                f"🗡️ {attacker} performs a mighty slash against {defender}!",
                f"⚔️ {attacker} swings their sword in a wide arc at {defender}!",
                f"🔪 {attacker} attempts to cut down {defender} with precision!"
            ],
            "thrust": [
                f"🗡️ {attacker} thrusts their blade towards {defender}!",
                f"⚔️ {attacker} attempts to pierce through {defender}'s defenses!",
                f"🔪 {attacker} launches a quick thrust at {defender}!"
            ],
            "defend": [
                f"🛡️ {defender} raises their shield!",
                f"🛡️ {defender} takes a defensive stance!",
                f"🛡️ {defender} prepares to block incoming attacks!"
            ]
        }
        base_msg = random.choice(messages[action])
        if action != "defend" and damage > 0:
            return f"{base_msg}\n💥 Dealing {damage} damage!"
        elif blocked > 0:
            return f"{base_msg}\n✨ Blocked {blocked} damage!"
        return base_msg

    async def _start_duel(self, ctx_or_interaction, opponent):
        if isinstance(ctx_or_interaction, discord.Interaction):
            user = ctx_or_interaction.user
            channel = ctx_or_interaction.channel
        else:
            user = ctx_or_interaction.author
            channel = ctx_or_interaction.channel

        if opponent.bot or opponent == user:
            msg = "You can't duel against bots or yourself!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        duel_state = {
            "players": {
                user.id: {"health": 100, "action": None, "defending": False},
                opponent.id: {"health": 100, "action": None, "defending": False}
            },
            "current_round": 1
        }

        class DuelButtons(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=30)

            @discord.ui.button(label="Slash", style=discord.ButtonStyle.danger, emoji="⚔️")
            async def slash(self, interaction: discord.Interaction, button: discord.ui.Button):
                await self.handle_action(interaction, "slash")

            @discord.ui.button(label="Thrust", style=discord.ButtonStyle.primary, emoji="🗡️")
            async def thrust(self, interaction: discord.Interaction, button: discord.ui.Button):
                await self.handle_action(interaction, "thrust")

            @discord.ui.button(label="Defend", style=discord.ButtonStyle.success, emoji="🛡️")
            async def defend(self, interaction: discord.Interaction, button: discord.ui.Button):
                await self.handle_action(interaction, "defend")

            async def handle_action(self, interaction: discord.Interaction, action):
                if interaction.user.id not in duel_state["players"]:
                    await interaction.response.send_message("You're not part of this duel!", ephemeral=True)
                    return

                player = duel_state["players"][interaction.user.id]
                if player["action"] is not None:
                    return

                player["action"] = action
                await interaction.response.defer()

                # Check if both players have acted
                if all(p["action"] is not None for p in duel_state["players"].values()):
                    self.stop()

        while True:
            # Reset actions
            for player in duel_state["players"].values():
                player["action"] = None
                player["defending"] = False

            embed = discord.Embed(title="⚔️ Medieval Duel ⚔️", color=discord.Color.gold())
            embed.add_field(name=f"{user.display_name}'s Health",
                          value=self.create_health_bar(duel_state["players"][user.id]["health"]),
                          inline=False)
            embed.add_field(name=f"{opponent.display_name}'s Health",
                          value=self.create_health_bar(duel_state["players"][opponent.id]["health"]),
                          inline=False)
            embed.set_footer(text=f"Round {duel_state['current_round']}")

            view = DuelButtons()
            
            if duel_state["current_round"] == 1:
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.response.send_message(embed=embed, view=view)
                    message = await ctx_or_interaction.original_response()
                else:
                    message = await ctx_or_interaction.send(embed=embed, view=view)
                duel_state["message"] = message
            else:
                await duel_state["message"].edit(embed=embed, view=view)

            try:
                await view.wait()
            except asyncio.TimeoutError:
                await channel.send("Duel timed out! Both fighters walked away.")
                return

            # Process actions
            p1_action = duel_state["players"][user.id]["action"]
            p2_action = duel_state["players"][opponent.id]["action"]

            action_text = []
            
            # Calculate damage
            for attacker_id, defender_id in [(user.id, opponent.id), (opponent.id, user.id)]:
                attacker = user if attacker_id == user.id else opponent
                defender = opponent if attacker_id == user.id else user
                
                attack_action = duel_state["players"][attacker_id]["action"]
                defend_action = duel_state["players"][defender_id]["action"]

                if attack_action in ["slash", "thrust"]:
                    base_damage = 20 if attack_action == "slash" else 25
                    damage = random.randint(base_damage - 5, base_damage + 5)
                    
                    if defend_action == "defend":
                        blocked = random.randint(10, 20)
                        damage = max(0, damage - blocked)
                        action_text.append(self.get_action_message("defend", attacker, defender, blocked=blocked))
                    
                    duel_state["players"][defender_id]["health"] -= damage
                    action_text.append(self.get_action_message(attack_action, attacker, defender, damage=damage))

            # Update embed with actions
            embed.description = "\n".join(action_text)
            await duel_state["message"].edit(embed=embed, view=None)

            # Check for winner
            for player_id, data in duel_state["players"].items():
                if data["health"] <= 0:
                    winner = opponent if player_id == user.id else user
                    loser = user if player_id == user.id else opponent
                    
                    final_embed = discord.Embed(
                        title="🏆 Duel Winner!",
                        description=f"{winner.mention} has defeated {loser.mention} in combat!",
                        color=discord.Color.gold()
                    )
                    await channel.send(embed=final_embed)
                    return

            duel_state["current_round"] += 1
            await asyncio.sleep(3)

async def setup(bot):
    await bot.add_cog(Duel(bot))
