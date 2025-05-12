import discord
import pymongo
import os
from discord.ext import commands
from discord import app_commands
from pymongo import MongoClient

class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Connect to MongoDB
        self.mongo_client = MongoClient(os.environ.get("MONGO_URI"))
        self.db = self.mongo_client['discord_economy']

    @commands.command(help="Ranks users based on their networth (only top 10.)", aliases=['lb', 'top', 'rich'])
    async def leaderboard(self, ctx):
        await self._show_leaderboard(ctx)

    @app_commands.command(name="leaderboard", description="Ranks users based on their networth (only top 10.)")
    async def leaderboard_slash(self, interaction: discord.Interaction):
        await self._show_leaderboard(interaction)

    async def _show_leaderboard(self, ctx_or_interaction):
        try:
            # Get the guild ID and guild object
            guild_id = ctx_or_interaction.guild.id if ctx_or_interaction.guild else None
            guild = ctx_or_interaction.guild
            
            if not guild:
                embed = discord.Embed(
                    title="Error",
                    description="This command can only be used in a server.",
                    color=0xE74C3C  # Red
                )
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await ctx_or_interaction.send(embed=embed)
                return
            
            # Get a list of all member IDs in the server
            member_ids = [str(member.id) for member in guild.members]
            
            # Find all economy records for members in this server
            user_data_list = list(self.db.economies.find(
                {"user_id": {"$in": member_ids}}
            ))
            
            # Calculate total money and sort
            for user_data in user_data_list:
                user_data['total'] = user_data.get('pocket', 0) + user_data.get('bank', 0)
            
            # Sort by total money (descending)
            user_totals = sorted(user_data_list, key=lambda x: x.get('total', 0), reverse=True)
            
            # Limit to top 10
            user_totals = user_totals[:10]
            
            embed = discord.Embed(
                title=f"🏆 Richest Users in {guild.name}",
                description="Server Leaderboard",
                color=0xF1C40F  # Gold color
            )

            if not user_totals:
                embed.add_field(
                    name="No users found",
                    value="Start earning money to appear on the leaderboard!",
                    inline=False
                )
            else:
                for i, user_data in enumerate(user_totals, 1):
                    try:
                        user = await self.bot.fetch_user(int(user_data["user_id"]))
                        total = user_data.get('total', 0)
                        pocket = user_data.get('pocket', 0)
                        bank = user_data.get('bank', 0)
                        
                        # Add medal emojis for top 3
                        prefix = ""
                        if i == 1:
                            prefix = "🥇 "
                        elif i == 2:
                            prefix = "🥈 "
                        elif i == 3:
                            prefix = "🥉 "
                        else:
                            prefix = f"{i}. "
                            
                        embed.add_field(
                            name=f"{prefix}{user.name}",
                            value=f"**Total**: ${total:,}\n**Pocket**: ${pocket:,} | **Bank**: ${bank:,}",
                            inline=False
                        )
                    except Exception as e:
                        print(f"Error fetching user for leaderboard: {e}")
                        continue
                        
            # Add footer with user's rank if they're not in top 10
            user_id = ctx_or_interaction.author.id if hasattr(ctx_or_interaction, 'author') else ctx_or_interaction.user.id
            
            # Check if user is already in the displayed leaderboard
            user_in_top = any(int(user_data.get("user_id")) == user_id for user_data in user_totals)
            
            if not user_in_top:
                # Find the user's position in this server's leaderboard
                user_data = self.db.economies.find_one({"user_id": str(user_id)})
                if user_data:
                    user_total = user_data.get('pocket', 0) + user_data.get('bank', 0)
                    
                    # Count server members with more money than this user
                    server_rank = 1
                    for member_id in member_ids:
                        if member_id == str(user_id):
                            continue
                            
                        member_data = self.db.economies.find_one({"user_id": member_id})
                        if member_data:
                            member_total = member_data.get('pocket', 0) + member_data.get('bank', 0)
                            if member_total > user_total:
                                server_rank += 1
                    
                    embed.set_footer(text=f"Your server rank: #{server_rank} with ${user_total:,}")

            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(embed=embed)
            else:
                await ctx_or_interaction.send(embed=embed)
                
        except Exception as e:
            print(f"Error in leaderboard: {e}")
            error_embed = discord.Embed(
                title="Error",
                description="An error occurred while retrieving the leaderboard.",
                color=0xE74C3C  # Red
            )
            
            if isinstance(ctx_or_interaction, discord.Interaction):
                if not ctx_or_interaction.response.is_done():
                    await ctx_or_interaction.response.send_message(embed=error_embed, ephemeral=True)
                else:
                    await ctx_or_interaction.followup.send(embed=error_embed, ephemeral=True)
            else:
                await ctx_or_interaction.send(embed=error_embed)

async def setup(bot):
    await bot.add_cog(Leaderboard(bot))