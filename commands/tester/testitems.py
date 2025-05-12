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

class TestItems(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Connect to MongoDB
        self.mongo_client = MongoClient(os.environ.get("MONGO_URI"))
        self.db = self.mongo_client['discord_economy']
        
        # List of test items that can be added
        self.test_items = {
            "banknote": {
                "name": "Bank Note",
                "description": "Increases your bank limit by 5,000",
                "price": 25000,
                "emoji": "📝"
            },
            "luckboost": {
                "name": "Luck Boost",
                "description": "Increases your luck by 10%, improving success rates in heists and steal commands",
                "price": 50000,
                "emoji": "🍀"
            },
            "theftshield": {
                "name": "Theft Shield",
                "description": "Protects your money from being stolen (one-time use)",
                "price": 100000,
                "emoji": "🛡️"
            }
        }
    
    @commands.command(name="getitem", help="Get an item for testing (Testers only)")
    @is_tester()
    async def getitem(self, ctx, item_name: str):
        await self._add_test_item(ctx, item_name.lower())
        
    @app_commands.command(name="getitem", description="Get an item for testing (Testers only)")
    @app_commands.describe(item_name="Name of the item to get (banknote, luckboost, theftshield)")
    @app_commands.choices(item_name=[
        app_commands.Choice(name="Bank Note", value="banknote"),
        app_commands.Choice(name="Luck Boost", value="luckboost"),
        app_commands.Choice(name="Theft Shield", value="theftshield")
    ])
    async def getitem_slash(self, interaction: discord.Interaction, item_name: str):
        # Check if the user is a tester
        if not is_tester_interaction(interaction):
            await interaction.response.send_message("Only testers can use this command.", ephemeral=True)
            return
            
        await self._add_test_item(interaction, item_name.lower())
    
    async def _add_test_item(self, ctx_or_interaction, item_name):
        # Check if item exists
        if item_name not in self.test_items:
            items_list = ", ".join(f"`{item}`" for item in self.test_items.keys())
            embed = discord.Embed(
                title="Invalid Item",
                description=f"Available items: {items_list}",
                color=0xE74C3C  # Red
            )
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await ctx_or_interaction.send(embed=embed)
            return
            
        # Get user ID
        user_id = ctx_or_interaction.author.id if hasattr(ctx_or_interaction, 'author') else ctx_or_interaction.user.id
        
        # Get item details
        item_details = self.test_items[item_name]
        
        # Add item to user's inventory
        self.db.economies.update_one(
            {"user_id": str(user_id)},
            {"$push": {"inventory": item_name}},
            upsert=True
        )
        
        # Create response embed
        embed = discord.Embed(
            title="Test Item Added",
            description=f"{item_details['emoji']} **{item_details['name']}** has been added to your inventory.",
            color=0x2ECC71  # Green
        )
        embed.add_field(name="Description", value=item_details['description'], inline=False)
        embed.add_field(name="Normal Price", value=f"${item_details['price']:,}", inline=True)
        
        # Send response
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)
    
    @commands.command(name="inventoryreset", help="Reset your inventory for testing (Testers only)")
    @is_tester()
    async def inventoryreset(self, ctx):
        await self._reset_inventory(ctx)
        
    @app_commands.command(name="inventoryreset", description="Reset your inventory for testing (Testers only)")
    async def inventoryreset_slash(self, interaction: discord.Interaction):
        # Check if the user is a tester
        if not is_tester_interaction(interaction):
            await interaction.response.send_message("Only testers can use this command.", ephemeral=True)
            return
            
        await self._reset_inventory(interaction)
    
    async def _reset_inventory(self, ctx_or_interaction):
        # Get user ID
        user_id = ctx_or_interaction.author.id if hasattr(ctx_or_interaction, 'author') else ctx_or_interaction.user.id
        
        # Reset user's inventory
        self.db.economies.update_one(
            {"user_id": str(user_id)},
            {"$set": {"inventory": []}},
            upsert=True
        )
        
        # Create response embed
        embed = discord.Embed(
            title="Inventory Reset",
            description="Your inventory has been reset to empty.",
            color=0xF39C12  # Orange
        )
        
        # Send response
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)

async def setup(bot):
    await bot.add_cog(TestItems(bot))