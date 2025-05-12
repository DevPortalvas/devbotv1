import discord
import os
from discord.ext import commands
from discord import app_commands
import datetime
import time
import random
from utils.database import update_balance, get_balance, get_shop_items, update_item_stock, update_bank_limit, update_luck, add_to_inventory
from utils.feedback import add_feedback_buttons

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="shop", help="View the available items in the shop")
    async def shop(self, ctx):
        await self._show_shop(ctx)

    @app_commands.command(name="shop", description="View the available items in the shop")
    async def shop_slash(self, interaction: discord.Interaction):
        await self._show_shop(interaction)

    @commands.command(name="buy", help="Buy an item from the shop")
    async def buy(self, ctx, item_id: str):
        await self._buy_item(ctx, item_id)

    @app_commands.command(name="buy", description="Buy an item from the shop")
    @app_commands.describe(item_id="The ID of the item to purchase")
    async def buy_slash(self, interaction: discord.Interaction, item_id: str):
        await self._buy_item(interaction, item_id)
        
    async def _show_shop(self, ctx_or_interaction):
        # Get user ID
        user_id = ctx_or_interaction.author.id if hasattr(ctx_or_interaction, 'author') else ctx_or_interaction.user.id
        
        # Get shop items
        items = get_shop_items()
        
        # Determine when shop refreshes
        from pymongo import MongoClient
        mongo_client = MongoClient(os.environ.get("MONGO_URI"))
        db = mongo_client['discord_economy']
        shop_data = db.shop.find_one({"id": "current_shop"})
        last_reset = shop_data.get("last_reset", time.time()) if shop_data else time.time()
        next_reset = last_reset + 10800  # 3 hours in seconds
        next_reset_timestamp = int(next_reset)
        
        # Create embed with fancy styling
        embed = discord.Embed(
            title="💎 PREMIUM SHOP 💎",
            description=(
                "Limited stock, items refresh every 3 hours!\n"
                f"Next restock <t:{next_reset_timestamp}:R>\n\n"
                "Use `d!buy <item_id>` to purchase an item."
            ),
            color=0x9B59B6  # Rich purple color
        )
        
        embed.set_thumbnail(url="https://i.imgur.com/gXrFC30.png")  # Shop icon
        
        # Add items to the embed
        if not items:
            embed.add_field(
                name="😔 SOLD OUT 😔",
                value="All items are currently sold out. Check back after the restock!",
                inline=False
            )
        else:
            for item in items:
                if item["stock"] > 0:
                    stock_status = f"📦 Stock: {item['stock']}"
                    embed.add_field(
                        name=f"🏷️ {item['name']} — ${item['price']:,}",
                        value=f"**ID**: `{item['id']}`\n{item['description']}\n{stock_status}",
                        inline=False
                    )
            
        # Get user balance
        try:
            balance = get_balance(None, user_id)
            pocket_balance = balance.get('pocket', 0)
            bank_balance = balance.get('bank', 0)
            bank_limit = balance.get('bank_limit', 10000)
            
            embed.add_field(
                name="💰 YOUR BALANCE",
                value=f"**Pocket**: ${pocket_balance:,}\n**Bank**: ${bank_balance:,}/{bank_limit:,}",
                inline=False
            )
        except Exception as e:
            print(f"Error getting balance in shop: {e}")
            
        # Add footer
        embed.set_footer(text="Items bought from the shop are consumed automatically • Premium economy system")
            
        # Add feedback buttons
        feedback_view = add_feedback_buttons("shop", user_id)
            
        # Send embed
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embed, view=feedback_view)
        else:
            message = await ctx_or_interaction.send(embed=embed, view=feedback_view)
            feedback_view.message = message

    async def _buy_item(self, ctx_or_interaction, item_id):
        # Get user
        user = ctx_or_interaction.author if hasattr(ctx_or_interaction, 'author') else ctx_or_interaction.user
        user_id = user.id
        
        # Get shop items
        items = get_shop_items()
        
        # Find the requested item
        target_item = None
        for item in items:
            if item["id"] == item_id:
                target_item = item
                break
                
        # Check if the item exists
        if not target_item:
            embed = discord.Embed(
                title="❌ Item Not Found",
                description=f"Item with ID `{item_id}` doesn't exist or is not currently in stock. Use `d!shop` to see available items.",
                color=0xE74C3C  # Red color
            )
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await ctx_or_interaction.send(embed=embed)
            return
            
        # Check if item is in stock
        if target_item["stock"] <= 0:
            embed = discord.Embed(
                title="❌ Out of Stock",
                description=f"Sorry, **{target_item['name']}** is currently out of stock. Check back after the next restock!",
                color=0xE74C3C
            )
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await ctx_or_interaction.send(embed=embed)
            return
            
        # Check if user has enough money
        try:
            balance = get_balance(None, user_id)
            pocket_balance = balance.get('pocket', 0)
            
            if pocket_balance < target_item["price"]:
                embed = discord.Embed(
                    title="❌ Insufficient Funds",
                    description=f"You need ${target_item['price']:,} to buy this item, but you only have ${pocket_balance:,} in your pocket.",
                    color=0xE74C3C
                )
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await ctx_or_interaction.send(embed=embed)
                return
                
            # Process purchase
            success = update_balance(None, user_id, -target_item["price"])
            if not success:
                embed = discord.Embed(
                    title="❌ Transaction Failed",
                    description="There was an error processing your transaction. Please try again.",
                    color=0xE74C3C
                )
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await ctx_or_interaction.send(embed=embed)
                return
                
            # Update item stock
            update_item_stock(target_item["id"], -1)
            
            # Handle item effects
            effect_description = ""
            if target_item["id"] == "banknote":
                # Increase bank limit by 5000
                current_limit = balance.get("bank_limit", 10000)
                new_limit = current_limit + 5000
                update_bank_limit(user_id, new_limit)
                effect_description = f"Your bank limit has increased from ${current_limit:,} to ${new_limit:,}!"
                
            elif target_item["id"] == "luck_boost":
                # Increase luck by 10%
                current_luck = balance.get("luck", 1.0)
                new_luck = current_luck + 0.1
                update_luck(user_id, new_luck)
                effect_description = f"Your luck has increased from {current_luck:.1f}x to {new_luck:.1f}x!"
                
            elif target_item["id"] == "shield":
                # Add shield to inventory with expiry time (24 hours from now)
                shield_data = {
                    "type": "shield",
                    "acquired": time.time(),
                    "expires": time.time() + 86400  # 24 hours
                }
                add_to_inventory(user_id, shield_data)
                expiry_time = int(shield_data["expires"])
                effect_description = f"You are now protected from theft for 24 hours! Expires <t:{expiry_time}:R>."
                
            elif target_item["id"] == "medal" or target_item["id"] == "mystery_box":
                # Just add to inventory
                item_data = {
                    "type": target_item["id"],
                    "acquired": time.time()
                }
                add_to_inventory(user_id, item_data)
                if target_item["id"] == "mystery_box":
                    # Random reward from mystery box
                    rewards = [
                        {"amount": 10000, "text": "found $10,000!"},
                        {"amount": 20000, "text": "found $20,000!"},
                        {"amount": 5000, "text": "found $5,000 and a discount coupon for your next purchase!"},
                        {"amount": 15000, "text": "found $15,000 and a rare collectible!"},
                        {"amount": 30000, "text": "hit the jackpot and found $30,000!"}
                    ]
                    import random
                    reward = random.choice(rewards)
                    update_balance(None, user_id, reward["amount"])
                    effect_description = f"You opened the mystery box and {reward['text']}"
                else:
                    effect_description = "The medal has been added to your collection!"
                
            # Create success embed
            embed = discord.Embed(
                title="✅ Purchase Successful",
                description=f"You bought **{target_item['name']}** for ${target_item['price']:,}!",
                color=0x2ECC71  # Green color
            )
            
            if effect_description:
                embed.add_field(name="✨ Item Effect", value=effect_description, inline=False)
                
            new_balance = pocket_balance - target_item["price"]
            embed.set_footer(text=f"Remaining balance: ${new_balance:,}")
            
            # Add feedback buttons for purchase
            feedback_view = add_feedback_buttons("buy", user.id)
            
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(embed=embed, view=feedback_view)
            else:
                message = await ctx_or_interaction.send(embed=embed, view=feedback_view)
                feedback_view.message = message
                
        except Exception as e:
            print(f"Error in buy command: {e}")
            error_embed = discord.Embed(
                title="Error",
                description="An unexpected error occurred while processing your purchase.",
                color=0xE74C3C
            )
            if isinstance(ctx_or_interaction, discord.Interaction):
                if not ctx_or_interaction.response.is_done():
                    await ctx_or_interaction.response.send_message(embed=error_embed, ephemeral=True)
                else:
                    await ctx_or_interaction.followup.send(embed=error_embed, ephemeral=True)
            else:
                await ctx_or_interaction.send(embed=error_embed)

async def setup(bot):
    await bot.add_cog(Shop(bot))