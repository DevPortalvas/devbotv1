import discord
from discord.ext import commands
from discord import app_commands
from utils.database import get_balance
from utils.feedback import add_feedback_buttons

class Inventory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Check your inventory of purchased items.", aliases=['inv', 'items'])
    async def inventory(self, ctx, member: discord.Member=None):
        await self._check_inventory(ctx, member)

    @app_commands.command(name="inventory", description="Check your inventory of purchased items")
    async def inventory_slash(self, interaction: discord.Interaction, member: discord.Member=None):
        await self._check_inventory(interaction, member)

    async def _check_inventory(self, ctx_or_interaction, member=None):
        try:
            user = member or (ctx_or_interaction.author if hasattr(ctx_or_interaction, 'author') else ctx_or_interaction.user)
            guild_id = ctx_or_interaction.guild.id
            
            try:
                bal = get_balance(guild_id, user.id)
                inventory = bal.get('inventory', [])
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

            embed = discord.Embed(title=f"{user.name}'s Inventory", color=discord.Color.blue())
            
            if not inventory:
                embed.description = "Your inventory is empty. Buy items from the shop!"
            else:
                # Group the same items and count them
                item_counts = {}
                for item in inventory:
                    item_id = item.get('id', 'unknown')
                    if item_id in item_counts:
                        item_counts[item_id]['count'] += 1
                    else:
                        item_counts[item_id] = {
                            'name': item.get('name', 'Unknown Item'),
                            'description': item.get('description', 'No description'),
                            'count': 1
                        }
                
                # Add each item to the embed
                for item_id, data in item_counts.items():
                    embed.add_field(
                        name=f"{data['name']} (x{data['count']})",
                        value=data['description'],
                        inline=False
                    )

            # Add feedback buttons
            feedback_view = add_feedback_buttons("inventory", user.id)
            
            if isinstance(ctx_or_interaction, discord.Interaction):
                if not ctx_or_interaction.response.is_done():
                    await ctx_or_interaction.response.send_message(embed=embed, view=feedback_view)
                else:
                    await ctx_or_interaction.followup.send(embed=embed, view=feedback_view)
            else:
                message = await ctx_or_interaction.send(embed=embed, view=feedback_view)
                feedback_view.message = message
                
        except Exception as e:
            print(f"General error in inventory command: {e}")
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
    await bot.add_cog(Inventory(bot))