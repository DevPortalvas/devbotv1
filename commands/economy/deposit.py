import discord
from discord.ext import commands
from discord import app_commands
from utils.database import get_balance, update_balance
from utils.feedback import add_feedback_buttons
  
class Deposit(commands.Cog):  
    def __init__(self, bot):  
        self.bot = bot  
  
    @commands.command(help="Deposit money into your bank.", aliases=['dep', 'put'])  
    async def deposit(self, ctx, amount):  
        await self._do_deposit(ctx, amount)  
  
    @app_commands.command(name="deposit", description="Deposit money into your bank")  
    @app_commands.describe(amount="Amount to deposit or 'all'")  
    async def deposit_slash(self, interaction: discord.Interaction, amount: str):  
        await self._do_deposit(interaction, amount)  
  
    async def _do_deposit(self, ctx_or_interaction, amount):  
        try:
            user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
            
            try:
                # Get global balance
                balance = get_balance(None, user.id)
            except Exception as db_error:
                print(f"Database error in deposit for user {user.id}: {db_error}")
                error_embed = discord.Embed(
                    title="Database Error",
                    description="Could not connect to the database. Please try again later.",
                    color=0xE74C3C
                )
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.response.send_message(embed=error_embed, ephemeral=True)
                else:
                    await ctx_or_interaction.send(embed=error_embed)
                return
        except Exception as e:
            print(f"Error in deposit: {e}")
            return
        
        # Check bank limit
        bank_limit = balance.get("bank_limit", 10000)
        current_bank = balance.get("bank", 0)
        available_space = bank_limit - current_bank
            
        if amount.lower() == "all":  
            amount_to_deposit = min(balance["pocket"], available_space)  
            if amount_to_deposit == 0:
                if available_space <= 0:
                    embed = discord.Embed(
                        title="⚠️ Bank Full",
                        description=(
                            f"Your bank is at capacity (${bank_limit:,}).\n"
                            "Purchase bank notes from the shop to increase your limit!"
                        ),
                        color=0xF39C12
                    )
                else:
                    embed = discord.Embed(
                        title="❌ No Money to Deposit",
                        description="You don't have any money in your pocket to deposit.",
                        color=0xE74C3C
                    )
                
                if isinstance(ctx_or_interaction, discord.Interaction):  
                    await ctx_or_interaction.response.send_message(embed=embed)  
                else:  
                    await ctx_or_interaction.send(embed=embed)
                return  
        else:  
            try:  
                amount_to_deposit = int(amount)  
            except ValueError:  
                embed = discord.Embed(
                    title="❌ Invalid Amount",
                    description="Please enter a valid number or 'all'.",
                    color=0xE74C3C
                )
                
                if isinstance(ctx_or_interaction, discord.Interaction):  
                    await ctx_or_interaction.response.send_message(embed=embed)  
                else:  
                    await ctx_or_interaction.send(embed=embed)
                return  
  
            if amount_to_deposit <= 0:
                embed = discord.Embed(
                    title="❌ Invalid Amount",
                    description="The amount must be more than 0.",
                    color=0xE74C3C
                )
                
                if isinstance(ctx_or_interaction, discord.Interaction):  
                    await ctx_or_interaction.response.send_message(embed=embed)  
                else:  
                    await ctx_or_interaction.send(embed=embed)
                return  
  
            if balance["pocket"] < amount_to_deposit:
                embed = discord.Embed(
                    title="❌ Insufficient Funds",
                    description=f"You only have ${balance['pocket']:,} in your pocket.",
                    color=0xE74C3C
                )
                
                if isinstance(ctx_or_interaction, discord.Interaction):  
                    await ctx_or_interaction.response.send_message(embed=embed)  
                else:  
                    await ctx_or_interaction.send(embed=embed)
                return
                
            # Check bank limit
            if amount_to_deposit > available_space:
                if available_space <= 0:
                    embed = discord.Embed(
                        title="⚠️ Bank Full",
                        description=(
                            f"Your bank is at capacity (${bank_limit:,}).\n"
                            "Purchase bank notes from the shop to increase your limit!"
                        ),
                        color=0xF39C12
                    )
                else:
                    embed = discord.Embed(
                        title="⚠️ Bank Almost Full",
                        description=(
                            f"You can only deposit ${available_space:,} more into your bank.\n"
                            f"Bank Limit: ${bank_limit:,}"
                        ),
                        color=0xF39C12
                    )
                    
                if isinstance(ctx_or_interaction, discord.Interaction):  
                    await ctx_or_interaction.response.send_message(embed=embed)  
                else:  
                    await ctx_or_interaction.send(embed=embed)
                return
  
        # Update balances
        update_balance(None, user.id, -amount_to_deposit, "pocket")
        update_balance(None, user.id, amount_to_deposit, "bank")
        
        # Get updated balance for display
        updated_balance = get_balance(None, user.id)
  
        embed = discord.Embed(  
            title="💸 Deposit Successful",  
            description=f"You deposited **${amount_to_deposit:,}** into your bank.",  
            color=0x2ECC71
        )
        
        embed.add_field(
            name="Balance",
            value=(
                f"**Pocket**: ${updated_balance['pocket']:,}\n"
                f"**Bank**: ${updated_balance['bank']:,}/{updated_balance['bank_limit']:,}"
            ),
            inline=False
        )
          
        # Add feedback buttons
        feedback_view = add_feedback_buttons("deposit", user.id)
            
        if isinstance(ctx_or_interaction, discord.Interaction):  
            await ctx_or_interaction.response.send_message(embed=embed, view=feedback_view)  
        else:  
            message = await ctx_or_interaction.send(embed=embed, view=feedback_view)
            feedback_view.message = message  
  
async def setup(bot):  
    await bot.add_cog(Deposit(bot))