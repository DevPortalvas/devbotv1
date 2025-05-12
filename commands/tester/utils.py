import discord
from discord.ext import commands
import os
from pymongo import MongoClient

# The owner ID
OWNER_ID = 545609811354583040

# MongoDB connection
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

# Empty setup function to prevent errors when the bot tries to load this as a cog
async def setup(bot):
    pass  # This is not a cog, but having this prevents errors