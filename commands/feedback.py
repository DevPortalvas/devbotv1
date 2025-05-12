import discord
from discord.ext import commands
from discord import app_commands
from utils.feedback import get_command_feedback_stats

# The owner ID
OWNER_ID = 545609811354583040

def is_owner():
    """Check if the user is the owner"""
    async def predicate(ctx):
        return ctx.author.id == OWNER_ID
    return commands.check(predicate)

class Feedback(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="feedback", help="View feedback statistics (Owner only)")
    @is_owner()
    async def feedback_stats(self, ctx, command_name: str = None):
        await self._show_feedback_stats(ctx, command_name)
    
    @app_commands.command(name="feedback", description="View feedback statistics (Owner only)")
    @app_commands.describe(command_name="The command to get feedback for (optional)")
    async def feedback_slash(self, interaction: discord.Interaction, command_name: str = None):
        # Check if the user is the owner
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("Only the bot owner can use this command.", ephemeral=True)
            return
        
        await self._show_feedback_stats(interaction, command_name)
    
    async def _show_feedback_stats(self, ctx_or_interaction, command_name=None):
        try:
            # Get feedback statistics
            stats = await get_command_feedback_stats(command_name)
            
            # Create embed
            embed = discord.Embed(
                title=f"Command Feedback Statistics{' for ' + command_name if command_name else ''}",
                color=0x9B59B6  # Purple
            )
            
            if not stats:
                embed.description = "No feedback data found."
            else:
                for cmd, data in stats.items():
                    positive = data.get("positive", 0)
                    negative = data.get("negative", 0)
                    total = positive + negative
                    
                    # Calculate positive percentage
                    positive_percent = (positive / total * 100) if total > 0 else 0
                    
                    # Create a visual bar chart
                    bar_length = 20
                    positive_bar = "▰" * int(positive_percent / 100 * bar_length)
                    negative_bar = "▱" * (bar_length - len(positive_bar))
                    
                    embed.add_field(
                        name=f"/{cmd}",
                        value=(
                            f"👍 **{positive}** | 👎 **{negative}**\n"
                            f"{positive_bar}{negative_bar} {positive_percent:.1f}%\n"
                            f"Total: {total} responses"
                        ),
                        inline=False
                    )
            
            # Send the embed
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await ctx_or_interaction.send(embed=embed)
                
        except Exception as e:
            print(f"Error getting feedback stats: {e}")
            error_message = "An error occurred while retrieving feedback statistics."
            
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(error_message, ephemeral=True)
            else:
                await ctx_or_interaction.send(error_message)

async def setup(bot):
    await bot.add_cog(Feedback(bot))