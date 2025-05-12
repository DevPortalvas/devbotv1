import discord
from discord.ext import commands
from discord import app_commands
import random
import re

class DiceRoller(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dice_pattern = re.compile(r'(\d+)d(\d+)([+-]\d+)?')

    @commands.command(name="dice", aliases=["r", "roll"], help="Roll dice with advanced notation (e.g. 2d20+5, 4d6, 1d100-2)")
    async def dice(self, ctx, *, dice_notation: str = "1d20"):
        await self._roll_dice(ctx, dice_notation)

    @app_commands.command(name="dice", description="Roll dice with advanced notation")
    @app_commands.describe(dice_notation="Dice notation (e.g. 2d20+5, 4d6, 1d100-2)")
    async def dice_slash(self, interaction: discord.Interaction, dice_notation: str = "1d20"):
        await self._roll_dice(interaction, dice_notation)

    async def _roll_dice(self, ctx_or_interaction, dice_notation):
        try:
            results = []
            total = 0
            notation_parts = dice_notation.replace(" ", "").lower().split(",")
            
            for part in notation_parts:
                match = self.dice_pattern.match(part)
                if not match:
                    error_embed = discord.Embed(
                        title="Invalid Dice Notation",
                        description="Please use formats like `2d6`, `1d20+5`, or `4d10-2`",
                        color=discord.Color.red()
                    )
                    if isinstance(ctx_or_interaction, discord.Interaction):
                        await ctx_or_interaction.response.send_message(embed=error_embed, ephemeral=True)
                    else:
                        await ctx_or_interaction.send(embed=error_embed)
                    return
                
                num_dice = int(match.group(1))
                dice_sides = int(match.group(2))
                modifier = int(match.group(3) or 0) if match.group(3) else 0
                
                # Limit for safety
                if num_dice > 100 or dice_sides > 1000:
                    error_embed = discord.Embed(
                        title="Dice Limit Exceeded",
                        description="Maximum 100 dice with up to 1000 sides each",
                        color=discord.Color.red()
                    )
                    if isinstance(ctx_or_interaction, discord.Interaction):
                        await ctx_or_interaction.response.send_message(embed=error_embed, ephemeral=True)
                    else:
                        await ctx_or_interaction.send(embed=error_embed)
                    return
                
                # Roll the dice
                rolls = [random.randint(1, dice_sides) for _ in range(num_dice)]
                
                # Calculate results
                sub_total = sum(rolls) + modifier
                total += sub_total
                
                # Format the result
                roll_display = ', '.join(str(r) for r in rolls)
                modifier_text = ""
                if modifier > 0:
                    modifier_text = f" + {modifier}"
                elif modifier < 0:
                    modifier_text = f" - {abs(modifier)}"
                
                results.append(f"**{part}**: [{roll_display}]{modifier_text} = **{sub_total}**")
            
            # Create embed
            author = ctx_or_interaction.author if hasattr(ctx_or_interaction, 'author') else ctx_or_interaction.user
            embed = discord.Embed(
                title="🎲 Dice Roller",
                description="\n".join(results),
                color=discord.Color.gold()
            )
            
            # Only show total if there are multiple dice notations
            if len(notation_parts) > 1:
                embed.add_field(name="Total", value=str(total), inline=False)
                
            embed.set_footer(text=f"Rolled by {author.display_name}")
            
            # Send the result
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(embed=embed)
            else:
                await ctx_or_interaction.send(embed=embed)
                
        except Exception as e:
            print(f"Error in dice roll: {e}")
            error_embed = discord.Embed(
                title="Error",
                description="An error occurred while processing your dice roll.",
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
    await bot.add_cog(DiceRoller(bot))