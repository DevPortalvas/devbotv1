import discord
from discord.ext import commands
from discord import app_commands
from utils.database import update_balance, get_balance

class ShopItem:
    def __init__(self, id, name, price, description, role_id=None):
        self.id = id
        self.name = name
        self.price = price
        self.description = description
        self.role_id = role_id  # Optional role ID to give when purchased

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.items = {
            # Default items - customize these as needed
            "1": ShopItem("1", "🥇 VIP Role", 50000, "Get the VIP role in the server"),
            "2": ShopItem("2", "🎮 Gamer Role", 25000, "Get the Gamer role in the server"),
            "3": ShopItem("3", "🎯 Custom Command", 75000, "Request a custom command just for you"),
            "4": ShopItem("4", "🎭 Custom Role", 100000, "Get a custom role with your choice of name and color"),
            "5": ShopItem("5", "🎨 Profile Banner", 30000, "Get a custom profile banner"),
        }
        self.guild_items = {}  # Guild ID -> {item_id: ShopItem}

    @commands.command(name="shop", help="View the server's shop")
    async def shop(self, ctx):
        await self._show_shop(ctx)

    @app_commands.command(name="shop", description="View the server's shop")
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
        # Get user and guild info
        guild_id = ctx_or_interaction.guild.id
        user_id = ctx_or_interaction.author.id if hasattr(ctx_or_interaction, 'author') else ctx_or_interaction.user.id
        
        # Get the items for this guild (or use default items)
        items = self.guild_items.get(guild_id, self.items)
        
        # Create embed
        embed = discord.Embed(
            title="🛒 Server Shop",
            description="Use `!buy <item_id>` to purchase an item.",
            color=discord.Color.blue()
        )
        
        # Add items to the embed
        for item_id, item in items.items():
            embed.add_field(
                name=f"[{item_id}] {item.name} - ${item.price:,}",
                value=item.description,
                inline=False
            )
            
        # Get user balance
        try:
            balance = get_balance(guild_id, user_id)
            pocket_balance = balance.get('pocket', 0)
            embed.set_footer(text=f"Your balance: ${pocket_balance:,}")
        except Exception as e:
            print(f"Error getting balance in shop: {e}")
            
        # Send embed
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)

    async def _buy_item(self, ctx_or_interaction, item_id):
        # Get user and guild info
        guild = ctx_or_interaction.guild
        guild_id = guild.id
        user = ctx_or_interaction.author if hasattr(ctx_or_interaction, 'author') else ctx_or_interaction.user
        user_id = user.id
        
        # Get the items for this guild (or use default items)
        items = self.guild_items.get(guild_id, self.items)
        
        # Check if the item exists
        if item_id not in items:
            embed = discord.Embed(
                title="❌ Item Not Found",
                description=f"Item with ID `{item_id}` doesn't exist. Use `!shop` to see available items.",
                color=discord.Color.red()
            )
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await ctx_or_interaction.send(embed=embed)
            return
            
        # Get the item
        item = items[item_id]
        
        # Check if user has enough money
        try:
            balance = get_balance(guild_id, user_id)
            pocket_balance = balance.get('pocket', 0)
            
            if pocket_balance < item.price:
                embed = discord.Embed(
                    title="❌ Insufficient Funds",
                    description=f"You need ${item.price:,} to buy this item, but you only have ${pocket_balance:,}.",
                    color=discord.Color.red()
                )
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await ctx_or_interaction.send(embed=embed)
                return
                
            # Process purchase
            update_balance(guild_id, user_id, -item.price)
            
            # Handle role rewards if applicable
            role_given = False
            if item.role_id:
                try:
                    role = guild.get_role(int(item.role_id))
                    if role:
                        await user.add_roles(role)
                        role_given = True
                except Exception as e:
                    print(f"Error giving role: {e}")
                    
            # Send success message
            embed = discord.Embed(
                title="✅ Purchase Successful",
                description=f"You bought **{item.name}** for ${item.price:,}!",
                color=discord.Color.green()
            )
            
            if role_given:
                embed.add_field(name="Role Added", value=f"You've been given the {role.name} role!", inline=False)
            else:
                embed.add_field(
                    name="Next Steps", 
                    value="Please contact a server administrator to claim your purchase.", 
                    inline=False
                )
                
            new_balance = pocket_balance - item.price
            embed.set_footer(text=f"Remaining balance: ${new_balance:,}")
            
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(embed=embed)
            else:
                await ctx_or_interaction.send(embed=embed)
                
        except Exception as e:
            print(f"Error in buy command: {e}")
            error_embed = discord.Embed(
                title="Error",
                description="An error occurred while processing your purchase.",
                color=discord.Color.red()
            )
            if isinstance(ctx_or_interaction, discord.Interaction):
                if not ctx_or_interaction.response.is_done():
                    await ctx_or_interaction.response.send_message(embed=error_embed, ephemeral=True)
                else:
                    await ctx_or_interaction.followup.send(embed=error_embed, ephemeral=True)
            else:
                await ctx_or_interaction.send(embed=error_embed)

    # Admin commands to manage the shop
    @commands.command(name="additem", help="Add an item to the shop (Admin only)")
    @commands.has_permissions(administrator=True)
    async def add_item(self, ctx, item_id: str, price: int, *, name_and_description):
        # Parse name and description
        parts = name_and_description.split('|', 1)
        if len(parts) != 2:
            await ctx.send("Format: !additem <id> <price> <name>|<description>")
            return
            
        name, description = parts
        
        # Initialize guild items if needed
        guild_id = ctx.guild.id
        if guild_id not in self.guild_items:
            self.guild_items[guild_id] = {}
            
        # Create and add the item
        self.guild_items[guild_id][item_id] = ShopItem(item_id, name.strip(), price, description.strip())
        
        await ctx.send(f"✅ Added item `{item_id}` to the shop!")

    @commands.command(name="removeitem", help="Remove an item from the shop (Admin only)")
    @commands.has_permissions(administrator=True)
    async def remove_item(self, ctx, item_id: str):
        guild_id = ctx.guild.id
        
        if guild_id not in self.guild_items or item_id not in self.guild_items[guild_id]:
            await ctx.send("❌ Item not found in this server's shop.")
            return
            
        del self.guild_items[guild_id][item_id]
        await ctx.send(f"✅ Removed item `{item_id}` from the shop!")

async def setup(bot):
    await bot.add_cog(Shop(bot))