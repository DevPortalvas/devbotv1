import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import time
import datetime
from utils.database import update_balance, get_balance, save_balance

class HeistButton(discord.ui.Button):
    def __init__(self, heist_manager):
        super().__init__(style=discord.ButtonStyle.green, label="Join Heist", emoji="💰")
        self.heist_manager = heist_manager
        
    async def callback(self, interaction: discord.Interaction):
        await self.heist_manager.add_member(interaction)

class HeistView(discord.ui.View):
    def __init__(self, heist_manager):
        super().__init__(timeout=60)  # 60 seconds to join
        self.add_item(HeistButton(heist_manager))
        self.heist_manager = heist_manager
        
    async def on_timeout(self):
        await self.heist_manager.start_heist()

class HeistManager:
    def __init__(self, bot, ctx_or_interaction, target_user):
        self.bot = bot
        self.ctx_or_interaction = ctx_or_interaction
        self.target = target_user
        self.channel = ctx_or_interaction.channel
        self.initiator = ctx_or_interaction.author if hasattr(ctx_or_interaction, 'author') else ctx_or_interaction.user
        self.members = [self.initiator]  # List of participants
        self.message = None
        self.view = HeistView(self)
        
    async def start_recruitment(self):
        # Check if target has money in bank
        target_balance = get_balance(None, self.target.id)
        target_bank = target_balance.get('bank', 0)
        
        if target_bank <= 0:
            embed = discord.Embed(
                title="🚫 Heist Cancelled",
                description=f"{self.target.mention} doesn't have any money in the bank!",
                color=0xE74C3C
            )
            
            if isinstance(self.ctx_or_interaction, discord.Interaction):
                if not self.ctx_or_interaction.response.is_done():
                    await self.ctx_or_interaction.response.send_message(embed=embed)
                else:
                    await self.ctx_or_interaction.followup.send(embed=embed)
            else:
                await self.ctx_or_interaction.send(embed=embed)
            return False
        
        # Check if initiator has money for the heist fee
        initiator_balance = get_balance(None, self.initiator.id)
        initiator_pocket = initiator_balance.get('pocket', 0)
        
        heist_fee = 2000  # Entry fee for heist
        
        if initiator_pocket < heist_fee:
            embed = discord.Embed(
                title="🚫 Heist Cancelled",
                description=f"You need ${heist_fee:,} in your pocket to initiate a heist!",
                color=0xE74C3C
            )
            
            if isinstance(self.ctx_or_interaction, discord.Interaction):
                if not self.ctx_or_interaction.response.is_done():
                    await self.ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await self.ctx_or_interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await self.ctx_or_interaction.send(embed=embed)
            return False
            
        # Deduct fee from initiator
        update_balance(None, self.initiator.id, -heist_fee)
        
        # Start recruitment
        embed = discord.Embed(
            title="🔫 BANK HEIST",
            description=(
                f"{self.initiator.mention} is planning a heist on {self.target.mention}'s bank!\n\n"
                f"**Target Bank Balance**: ${target_bank:,}\n\n"
                "**Click the button below to join the heist!**\n"
                "⚠️ There's a risk you could lose all your money if caught!\n"
                "**Entry Fee**: $2,000\n\n"
                f"**Current Crew ({len(self.members)}/5)**:\n"
                f"• {self.initiator.mention}"
            ),
            color=0x9B59B6
        )
        
        embed.set_thumbnail(url="https://i.imgur.com/3MXF6Pq.png")  # Heist icon
        embed.set_footer(text="Recruitment closes in 60 seconds | Minimum 2 crew members needed")
        
        if isinstance(self.ctx_or_interaction, discord.Interaction):
            if not self.ctx_or_interaction.response.is_done():
                await self.ctx_or_interaction.response.send_message(embed=embed, view=self.view)
                self.message = await self.ctx_or_interaction.original_response()
            else:
                self.message = await self.ctx_or_interaction.followup.send(embed=embed, view=self.view)
        else:
            self.message = await self.ctx_or_interaction.send(embed=embed, view=self.view)
        
        return True
    
    async def add_member(self, interaction: discord.Interaction):
        user = interaction.user
        
        # Check if already a member
        if user in self.members:
            await interaction.response.send_message("You're already part of this heist!", ephemeral=True)
            return
            
        # Check if target
        if user.id == self.target.id:
            await interaction.response.send_message("You can't join a heist targeting yourself!", ephemeral=True)
            return
            
        # Check if user has money for the heist fee
        balance = get_balance(None, user.id)
        pocket_balance = balance.get('pocket', 0)
        
        heist_fee = 2000  # Entry fee for heist
        
        if pocket_balance < heist_fee:
            await interaction.response.send_message(f"You need ${heist_fee:,} in your pocket to join the heist!", ephemeral=True)
            return
            
        # Check if max members reached
        if len(self.members) >= 5:
            await interaction.response.send_message("This heist crew is full!", ephemeral=True)
            return
            
        # Deduct fee from user
        update_balance(None, user.id, -heist_fee)
        
        # Add user to members
        self.members.append(user)
        
        # Update the embed
        members_text = "\n".join([f"• {member.mention}" for member in self.members])
        
        embed = discord.Embed(
            title="🔫 BANK HEIST",
            description=(
                f"{self.initiator.mention} is planning a heist on {self.target.mention}'s bank!\n\n"
                f"**Target Bank Balance**: ${get_balance(None, self.target.id).get('bank', 0):,}\n\n"
                "**Click the button below to join the heist!**\n"
                "⚠️ There's a risk you could lose all your money if caught!\n"
                "**Entry Fee**: $2,000\n\n"
                f"**Current Crew ({len(self.members)}/5)**:\n"
                f"{members_text}"
            ),
            color=0x9B59B6
        )
        
        embed.set_thumbnail(url="https://i.imgur.com/3MXF6Pq.png")
        embed.set_footer(text="Recruitment closes in 60 seconds | Minimum 2 crew members needed")
        
        await self.message.edit(embed=embed)
        await interaction.response.send_message("You've joined the heist!", ephemeral=True)
    
    async def start_heist(self):
        # Need at least 2 members
        if len(self.members) < 2:
            embed = discord.Embed(
                title="🚫 Heist Cancelled",
                description="Not enough crew members joined. Minimum 2 required!\nEntry fees have been refunded.",
                color=0xE74C3C
            )
            
            # Refund fees
            for member in self.members:
                update_balance(None, member.id, 2000)
                
            await self.message.edit(embed=embed, view=None)
            return
            
        # Get target's bank balance
        target_balance = get_balance(None, self.target.id)
        target_bank = target_balance.get('bank', 0)
        
        # Begin heist animation
        loading_embed = discord.Embed(
            title="🔫 HEIST IN PROGRESS",
            description="The crew is moving in on the target...",
            color=0xF39C12
        )
        
        await self.message.edit(embed=loading_embed, view=None)
        await asyncio.sleep(3)
        
        # Determine success chance based on crew size and luck
        success_chance = 0.3 + (len(self.members) * 0.1)  # 40% for 1 member, up to 80% for 5 members
        
        # Add luck bonus
        crew_luck = 1.0
        for member in self.members:
            member_luck = get_balance(None, member.id).get('luck', 1.0)
            crew_luck += (member_luck - 1.0) / len(self.members)  # Average crew luck bonus
            
        success_chance *= crew_luck
        success_chance = min(success_chance, 0.9)  # Cap at 90%
        
        # Determine outcome
        success = random.random() < success_chance
        
        if success:
            # Calculate loot amount (25-75% of target's bank)
            loot_percentage = random.uniform(0.25, 0.75)
            loot_amount = int(target_bank * loot_percentage)
            
            # Reduce target's bank balance
            update_balance(None, self.target.id, -loot_amount, "bank")
            
            # Distribute loot
            share_per_member = loot_amount // len(self.members)
            
            # Create list of members who survived (90% chance per member)
            survivors = []
            casualties = []
            
            casualty_messages = [
                "got caught in a shootout with guards.",
                "triggered the alarm system.",
                "was identified by security cameras.",
                "slipped on a banana peel and knocked themselves out.",
                "accidentally revealed their identity."
            ]
            
            for member in self.members:
                survived = random.random() < 0.9  # 90% survival rate
                if survived:
                    survivors.append(member)
                    update_balance(None, member.id, share_per_member)
                else:
                    casualties.append({
                        "member": member,
                        "reason": random.choice(casualty_messages)
                    })
                    # Reset their balance to 0 in both pocket and bank
                    save_balance(None, member.id, {"pocket": 0, "bank": 0})
            
            # Create success embed
            success_embed = discord.Embed(
                title="💰 HEIST SUCCESSFUL",
                description=(
                    f"Your crew successfully robbed {self.target.mention}'s bank!\n\n"
                    f"**Total Loot**: ${loot_amount:,}\n"
                    f"**Share Per Survivor**: ${share_per_member:,}\n\n"
                ),
                color=0x2ECC71
            )
            
            # Add survivors section
            if survivors:
                survivors_text = "\n".join([f"• {member.mention} — +${share_per_member:,}" for member in survivors])
                success_embed.add_field(
                    name=f"✅ Survivors ({len(survivors)}/{len(self.members)})",
                    value=survivors_text,
                    inline=False
                )
            
            # Add casualties section
            if casualties:
                casualties_text = "\n".join([f"• {casualty['member'].mention} — {casualty['reason']} **LOST EVERYTHING!**" for casualty in casualties])
                success_embed.add_field(
                    name=f"☠️ Casualties ({len(casualties)}/{len(self.members)})",
                    value=casualties_text,
                    inline=False
                )
            
            success_embed.set_footer(text="Successful heists increase security. Try again after the heat dies down.")
            
            await self.message.edit(embed=success_embed)
            
        else:
            # Heist failed, reset everyone's balance
            failed_embed = discord.Embed(
                title="🚨 HEIST FAILED",
                description=(
                    f"Your crew was caught trying to rob {self.target.mention}'s bank!\n\n"
                    "**The alarm was triggered and everyone was arrested.**\n\n"
                ),
                color=0xE74C3C
            )
            
            # Create list of captured crew with random reasons
            capture_messages = [
                "was tackled by security guards.",
                "tripped the laser security system.",
                "was identified by surveillance cameras.",
                "was caught hiding in a bathroom stall.",
                "was betrayed by an anonymous tip.",
                "dropped their wallet at the crime scene."
            ]
            
            captured_text = ""
            for member in self.members:
                reason = random.choice(capture_messages)
                captured_text += f"• {member.mention} — {reason} **LOST EVERYTHING!**\n"
                
                # Reset their balance to 0 in both pocket and bank
                save_balance(None, member.id, {"pocket": 0, "bank": 0})
            
            failed_embed.add_field(
                name="🚔 Captured Crew",
                value=captured_text,
                inline=False
            )
            
            failed_embed.set_footer(text="Better luck next time... if you get out of prison!")
            
            await self.message.edit(embed=failed_embed)

class Heist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_heists = {}  # Channel ID -> HeistManager
        
    @commands.command(name="heist", help="Start a heist on another user's bank")
    async def heist(self, ctx, target: discord.Member):
        await self._start_heist(ctx, target)
        
    @app_commands.command(name="heist", description="Start a heist on another user's bank")
    @app_commands.describe(target="The user whose bank you want to rob")
    async def heist_slash(self, interaction: discord.Interaction, target: discord.Member):
        await self._start_heist(interaction, target)
        
    async def _start_heist(self, ctx_or_interaction, target):
        # Check if targeting self
        initiator = ctx_or_interaction.author if hasattr(ctx_or_interaction, 'author') else ctx_or_interaction.user
        
        if initiator.id == target.id:
            embed = discord.Embed(
                title="❌ Error",
                description="You can't start a heist on your own bank!",
                color=0xE74C3C
            )
            
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await ctx_or_interaction.send(embed=embed)
            return
            
        # Check if bot
        if target.bot:
            embed = discord.Embed(
                title="❌ Error",
                description="You can't rob a bot's bank!",
                color=0xE74C3C
            )
            
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await ctx_or_interaction.send(embed=embed)
            return
            
        # Check if heist already active in channel
        channel = ctx_or_interaction.channel
        if channel.id in self.active_heists:
            embed = discord.Embed(
                title="⚠️ Heist Already Active",
                description="There's already a heist being planned in this channel!",
                color=0xF39C12
            )
            
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await ctx_or_interaction.send(embed=embed)
            return
            
        # Check for shield
        target_balance = get_balance(None, target.id)
        target_inventory = target_balance.get("inventory", [])
        
        for item in target_inventory:
            if item.get("type") == "shield" and item.get("expires", 0) > time.time():
                embed = discord.Embed(
                    title="🛡️ Target Protected",
                    description=f"{target.mention} is currently protected by a shield!",
                    color=0xF39C12
                )
                
                expiry_time = int(item.get("expires"))
                embed.set_footer(text=f"Shield expires {discord.utils.format_dt(datetime.datetime.fromtimestamp(expiry_time), 'R')}")
                
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await ctx_or_interaction.send(embed=embed)
                return
            
        # Start heist
        heist_manager = HeistManager(self.bot, ctx_or_interaction, target)
        self.active_heists[channel.id] = heist_manager
        
        success = await heist_manager.start_recruitment()
        
        if success:
            # Remove from active heists after 70 seconds (10 more than button timeout)
            await asyncio.sleep(70)
            if channel.id in self.active_heists:
                del self.active_heists[channel.id]

async def setup(bot):
    await bot.add_cog(Heist(bot))