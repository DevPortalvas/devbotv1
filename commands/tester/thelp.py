import discord
from discord.ext import commands
from discord import app_commands
import os
from pymongo import MongoClient

# The owner ID
OWNER_ID = 545609811354583040

# MongoDB connection for checking testers
mongo_client = MongoClient(os.environ.get("MONGO_URI"))
db = mongo_client['discord_economy']

def is_tester():
    """Check if user is a tester or the owner"""
    async def predicate(ctx):
        # Always allow the owner
        if ctx.author.id == OWNER_ID:
            return True
            
        # Check if user is in the testers collection
        tester = db.testers.find_one({"user_id": str(ctx.author.id)})
        return tester is not None
    
    return commands.check(predicate)

def is_tester_interaction(interaction):
    """Check if interaction user is a tester or the owner"""
    # Always allow the owner
    if interaction.user.id == OWNER_ID:
        return True
        
    # Check if user is in the testers collection
    tester = db.testers.find_one({"user_id": str(interaction.user.id)})
    return tester is not None

class TesterHelp(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # List of tester-only commands with descriptions
        self.tester_commands = [
            {"name": "thelp", "description": "Shows this help menu for tester commands"},
            {"name": "addtester", "description": "Adds a user as a tester (Owner only)"},
            {"name": "removetester", "description": "Removes a user as a tester (Owner only)"},
            {"name": "listtesters", "description": "Lists all testers (Owner only)"},
            {"name": "testmoney", "description": "Get testing money (Testers only)"},
            {"name": "resetmoney", "description": "Reset your money for testing (Testers only)"},
            {"name": "getitem", "description": "Get an item for testing (Testers only)"},
            {"name": "inventoryreset", "description": "Reset your inventory for testing (Testers only)"},
        ]
        
    @commands.command(name="thelp", help="Shows tester commands (Testers only)")
    @is_tester()
    async def thelp(self, ctx):
        await self._show_tester_help(ctx)
        
    @app_commands.command(name="thelp", description="Shows tester commands (Testers only)")
    async def thelp_slash(self, interaction: discord.Interaction):
        # Check if the user is a tester
        if not is_tester_interaction(interaction):
            await interaction.response.send_message("Only testers can use this command.", ephemeral=True)
            return
            
        await self._show_tester_help(interaction)
    
    async def _show_tester_help(self, ctx_or_interaction):
        embed = discord.Embed(
            title="🧪 Tester Commands",
            description="These commands are only available to testers and won't show in the regular help command.",
            color=0x9B59B6  # Purple
        )
        
        # Add fields for each command
        for cmd in self.tester_commands:
            embed.add_field(
                name=f"d!{cmd['name']}",
                value=cmd['description'],
                inline=False
            )
            
        embed.set_footer(text="These commands are hidden from regular users")
        
        # Send the help message
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await ctx_or_interaction.send(embed=embed)

async def setup(bot):
    await bot.add_cog(TesterHelp(bot))