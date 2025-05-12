import discord
from discord.ext import commands
from discord import app_commands
import random
from utils.database import update_balance, get_balance
import time
import datetime
from utils.feedback import add_feedback_buttons

class Daily(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}  # Guild ID -> {User ID -> last claim time}
        self.cooldown_time = 86400  # 24 hours in seconds
        self.streaks = {}  # Guild ID -> {User ID -> streak count}
        
    @commands.command(name="daily", help="Claim your daily reward. Consecutive days build a streak for bonus rewards!")
    async def daily(self, ctx):
        await self._claim_daily(ctx)
        
    @app_commands.command(name="daily", description="Claim your daily reward and build streak bonuses")
    async def daily_slash(self, interaction: discord.Interaction):
        await self._claim_daily(interaction)
        
    async def _claim_daily(self, ctx_or_interaction):
        try:
            # Get user and guild info
            user = ctx_or_interaction.author if hasattr(ctx_or_interaction, 'author') else ctx_or_interaction.user
            guild_id = ctx_or_interaction.guild.id
            user_id = user.id
            
            # Initialize guild data in the cooldowns dict if not exists
            if guild_id not in self.cooldowns:
                self.cooldowns[guild_id] = {}
                self.streaks[guild_id] = {}
                
            current_time = int(time.time())
            last_claim = self.cooldowns[guild_id].get(user_id, 0)
            time_passed = current_time - last_claim
            
            # Check if on cooldown
            if time_passed < self.cooldown_time and last_claim > 0:
                remaining = self.cooldown_time - time_passed
                next_reset = datetime.datetime.now() + datetime.timedelta(seconds=remaining)
                next_reset_str = f"<t:{int(next_reset.timestamp())}:R>"
                
                embed = discord.Embed(
                    title="Daily Reward - On Cooldown",
                    description=f"You've already claimed your daily reward today.\nYou can claim again {next_reset_str}",
                    color=discord.Color.red()
                )
                
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await ctx_or_interaction.send(embed=embed)
                return
                
            # Calculate streak
            current_streak = self.streaks[guild_id].get(user_id, 0)
            
            # If it's been between 1 and 2 days (a bit of leeway), maintain streak
            # If it's been over 2 days, reset streak
            if time_passed > self.cooldown_time * 2 and last_claim > 0:
                current_streak = 0
                
            # Increment streak
            current_streak += 1
            self.streaks[guild_id][user_id] = current_streak
            
            # Calculate bonus based on streak
            base_amount = random.randint(1000, 3000)
            streak_bonus = min(current_streak * 100, 1000)  # Cap at 1000 bonus
            total_reward = base_amount + streak_bonus
            
            # Update user's balance
            update_balance(guild_id, user_id, total_reward)
            
            # Create embed
            embed = discord.Embed(
                title="Daily Reward Claimed!",
                description=f"You received **${base_amount:,}** as your daily reward!",
                color=discord.Color.green()
            )
            
            if streak_bonus > 0:
                embed.add_field(
                    name="Streak Bonus", 
                    value=f"**{current_streak}** day streak: +**${streak_bonus:,}**", 
                    inline=False
                )
                
            embed.add_field(
                name="Total Reward", 
                value=f"**${total_reward:,}**", 
                inline=False
            )
            
            # Get current balance
            try:
                balance = get_balance(guild_id, user_id)
                embed.add_field(
                    name="Current Balance",
                    value=f"Pocket: **${balance.get('pocket', 0):,}**\nBank: **${balance.get('bank', 0):,}**",
                    inline=False
                )
            except Exception:
                pass  # Skip balance display if there's an error
                
            # Add streak info
            if current_streak > 1:
                next_bonus = min((current_streak + 1) * 100, 1000)
                embed.set_footer(text=f"Current streak: {current_streak} days | Next streak bonus: ${next_bonus}")
            else:
                embed.set_footer(text=f"Come back tomorrow to start a streak and earn bonus rewards!")
                
            # Update cooldown
            self.cooldowns[guild_id][user_id] = current_time
            
            # Add feedback buttons
            feedback_view = add_feedback_buttons("daily", user_id)
            
            # Send response
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(embed=embed, view=feedback_view)
            else:
                message = await ctx_or_interaction.send(embed=embed, view=feedback_view)
                feedback_view.message = message
                
        except Exception as e:
            print(f"Error in daily command: {e}")
            error_embed = discord.Embed(
                title="Error",
                description="An error occurred while processing your daily reward.",
                color=discord.Color.red()
            )
            if isinstance(ctx_or_interaction, discord.Interaction):
                if not ctx_or_interaction.response.is_done():
                    await ctx_or_interaction.response.send_message(embed=error_embed, ephemeral=True)
                else:
                    await ctx_or_interaction.followup.send(embed=error_embed, ephemeral=True)
            else:
                await ctx_or_interaction.send(embed=error_embed)

async def setup(bot):
    await bot.add_cog(Daily(bot))