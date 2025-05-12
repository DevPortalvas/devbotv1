import discord
from discord.ext import commands
from discord import app_commands
import pymongo
import os
from pymongo import MongoClient

def is_owner():
    """Check if the user is the owner (545609811354583040)"""
    async def predicate(ctx):
        return ctx.author.id == 545609811354583040
    return commands.check(predicate)

class AddTester(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.owner_id = 545609811354583040
        # Connect to MongoDB for storing testers
        self.mongo_client = MongoClient(os.environ.get("MONGO_URI"))
        self.db = self.mongo_client['discord_economy']
        
        # Create testers collection if it doesn't exist
        if "testers" not in self.db.list_collection_names():
            self.db.create_collection("testers")
    
    @commands.command(name="addtester", help="Add a user as a tester (Owner only)")
    @is_owner()
    async def addtester(self, ctx, user: discord.Member):
        await self._add_tester(ctx, user)
        
    @app_commands.command(name="addtester", description="Add a user as a tester (Owner only)")
    @app_commands.describe(user="The user to add as a tester")
    async def addtester_slash(self, interaction: discord.Interaction, user: discord.Member):
        # Check if the caller is the owner
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Only the bot owner can use this command.", ephemeral=True)
            return
            
        await self._add_tester(interaction, user)
    
    async def _add_tester(self, ctx_or_interaction, user):
        # Check if already a tester
        existing_tester = self.db.testers.find_one({"user_id": str(user.id)})
        if existing_tester:
            embed = discord.Embed(
                title="Tester Already Exists",
                description=f"{user.mention} is already a tester.",
                color=0xE74C3C  # Red
            )
        else:
            # Add to testers
            self.db.testers.insert_one({
                "user_id": str(user.id),
                "username": user.name,
                "added_by": str(self.owner_id),
                "added_at": discord.utils.utcnow().timestamp()
            })
            
            embed = discord.Embed(
                title="Tester Added",
                description=f"{user.mention} has been added as a tester.\nThey can now use all testing commands.",
                color=0x2ECC71  # Green
            )
            
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)

    @commands.command(name="removetester", help="Remove a user as a tester (Owner only)")
    @is_owner()
    async def removetester(self, ctx, user: discord.Member):
        await self._remove_tester(ctx, user)
    
    @app_commands.command(name="removetester", description="Remove a user as a tester (Owner only)")
    @app_commands.describe(user="The user to remove as a tester")
    async def removetester_slash(self, interaction: discord.Interaction, user: discord.Member):
        # Check if the caller is the owner
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Only the bot owner can use this command.", ephemeral=True)
            return
            
        await self._remove_tester(interaction, user)
    
    async def _remove_tester(self, ctx_or_interaction, user):
        # Check if user is a tester
        existing_tester = self.db.testers.find_one({"user_id": str(user.id)})
        
        if not existing_tester:
            embed = discord.Embed(
                title="Not a Tester",
                description=f"{user.mention} is not a tester.",
                color=0xE74C3C  # Red
            )
        else:
            # Remove from testers
            self.db.testers.delete_one({"user_id": str(user.id)})
            
            embed = discord.Embed(
                title="Tester Removed",
                description=f"{user.mention} has been removed as a tester.",
                color=0xF39C12  # Orange
            )
            
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)
    
    @commands.command(name="listtesters", help="List all current testers (Owner only)")
    @is_owner()
    async def listtesters(self, ctx):
        await self._list_testers(ctx)
    
    @app_commands.command(name="listtesters", description="List all current testers (Owner only)")
    async def listtesters_slash(self, interaction: discord.Interaction):
        # Check if the caller is the owner
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Only the bot owner can use this command.", ephemeral=True)
            return
            
        await self._list_testers(interaction)
    
    async def _list_testers(self, ctx_or_interaction):
        # Get all testers
        testers = list(self.db.testers.find())
        
        embed = discord.Embed(
            title="Bot Testers",
            description=f"Total Testers: {len(testers)}",
            color=0x3498DB  # Blue
        )
        
        if not testers:
            embed.add_field(name="No Testers", value="No testers have been added yet.", inline=False)
        else:
            tester_list = ""
            for i, tester in enumerate(testers, 1):
                user_id = tester.get("user_id")
                username = tester.get("username", "Unknown")
                try:
                    user = await self.bot.fetch_user(int(user_id))
                    username = user.name
                except:
                    pass
                    
                tester_list += f"{i}. {username} (ID: {user_id})\n"
                
            embed.add_field(name="Tester List", value=tester_list, inline=False)
        
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AddTester(bot))