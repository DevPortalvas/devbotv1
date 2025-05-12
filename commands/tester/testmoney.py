import discord
from discord.ext import commands
from discord import app_commands
import pymongo
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

class TestMoney(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Connect to MongoDB
        self.mongo_client = MongoClient(os.environ.get("MONGO_URI"))
        self.db = self.mongo_client['discord_economy']
    
    @commands.command(name="testmoney", help="Get money for testing purposes (Testers only)")
    @is_tester()
    async def testmoney(self, ctx, amount: int = 10000):
        await self._add_test_money(ctx, amount)
        
    @app_commands.command(name="testmoney", description="Get money for testing purposes (Testers only)")
    @app_commands.describe(amount="Amount of money to add (default: 10,000)")
    async def testmoney_slash(self, interaction: discord.Interaction, amount: int = 10000):
        # Check if the user is a tester
        if not is_tester_interaction(interaction):
            await interaction.response.send_message("Only testers can use this command.", ephemeral=True)
            return
            
        await self._add_test_money(interaction, amount)
    
    async def _add_test_money(self, ctx_or_interaction, amount):
        # Validate amount
        if amount <= 0:
            embed = discord.Embed(
                title="Invalid Amount",
                description="Amount must be positive.",
                color=0xE74C3C  # Red
            )
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await ctx_or_interaction.send(embed=embed)
            return
            
        # Limit amount to 1 million per request
        if amount > 1000000:
            amount = 1000000
            limit_message = "Amount limited to 1,000,000 per request."
        else:
            limit_message = ""
            
        # Get user ID
        user_id = ctx_or_interaction.author.id if hasattr(ctx_or_interaction, 'author') else ctx_or_interaction.user.id
        
        # Add money to user's pocket
        user_data = self.db.economies.find_one({"user_id": str(user_id)})
        
        if user_data:
            # Update existing user
            current_pocket = user_data.get("pocket", 0)
            new_pocket = current_pocket + amount
            
            self.db.economies.update_one(
                {"user_id": str(user_id)},
                {"$set": {"pocket": new_pocket}}
            )
        else:
            # Create new user entry
            self.db.economies.insert_one({
                "user_id": str(user_id),
                "pocket": amount,
                "bank": 0,
                "bank_limit": 10000,  # Default bank limit
                "luck": 0,            # Default luck factor
                "inventory": []
            })
            
        # Create response embed
        embed = discord.Embed(
            title="Testing Money Added",
            description=f"Added ${amount:,} to your pocket for testing purposes.\n{limit_message}",
            color=0x2ECC71  # Green
        )
        
        # Send response
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)
    
    @commands.command(name="resetmoney", help="Reset your money for testing (Testers only)")
    @is_tester()
    async def resetmoney(self, ctx):
        await self._reset_money(ctx)
        
    @app_commands.command(name="resetmoney", description="Reset your money for testing (Testers only)")
    async def resetmoney_slash(self, interaction: discord.Interaction):
        # Check if the user is a tester
        if not is_tester_interaction(interaction):
            await interaction.response.send_message("Only testers can use this command.", ephemeral=True)
            return
            
        await self._reset_money(interaction)
    
    async def _reset_money(self, ctx_or_interaction):
        # Get user ID
        user_id = ctx_or_interaction.author.id if hasattr(ctx_or_interaction, 'author') else ctx_or_interaction.user.id
        
        # Reset user's money
        self.db.economies.update_one(
            {"user_id": str(user_id)},
            {"$set": {"pocket": 0, "bank": 0, "bank_limit": 10000, "luck": 0}},
            upsert=True
        )
        
        # Create response embed
        embed = discord.Embed(
            title="Money Reset",
            description="Your pocket and bank balances have been reset to 0.\nBank limit has been reset to 10,000.\nLuck factor has been reset to 0.",
            color=0xF39C12  # Orange
        )
        
        # Send response
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)

async def setup(bot):
    await bot.add_cog(TestMoney(bot))