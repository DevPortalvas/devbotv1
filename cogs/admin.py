import discord
from discord.ext import commands
import logging
import asyncio

logger = logging.getLogger("bot")

class Admin(commands.Cog):
    """Admin commands for the bot"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def cog_check(self, ctx):
        """Check if the user has admin permissions"""
        if ctx.guild is None:
            return False
        return ctx.author.guild_permissions.administrator
    
    @commands.command(name="prefix")
    async def set_prefix(self, ctx, new_prefix=None):
        """Set the command prefix for this server"""
        if new_prefix is None:
            # Display current prefix
            current_prefix = "!"  # Default prefix
            guild_data = await self.bot.db.get_guild_settings(ctx.guild.id)
            if guild_data and "prefix" in guild_data:
                current_prefix = guild_data["prefix"]
                
            await ctx.send(f"Current prefix is: `{current_prefix}`")
        else:
            # Update prefix
            if len(new_prefix) > 5:
                await ctx.send("Prefix cannot be longer than 5 characters.")
                return
                
            success = await self.bot.db.update_guild_settings(ctx.guild.id, {"prefix": new_prefix})
            if success:
                await ctx.send(f"Prefix updated to: `{new_prefix}`")
            else:
                await ctx.send("Failed to update prefix. Please try again later.")
    
    @commands.command(name="purge")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int):
        """Delete a specified number of messages from the channel"""
        if amount <= 0 or amount > 100:
            await ctx.send("Please specify a number between 1 and 100.")
            return
            
        deleted = await ctx.channel.purge(limit=amount + 1)  # +1 to include the command message
        
        # Send confirmation and delete it after 5 seconds
        confirm_message = await ctx.send(f"Deleted {len(deleted) - 1} messages.")
        await asyncio.sleep(5)
        await confirm_message.delete()
    
    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        """Kick a member from the server"""
        if ctx.author.top_role <= member.top_role:
            await ctx.send("You cannot kick someone with a higher or equal role.")
            return
            
        try:
            await member.kick(reason=reason)
            embed = discord.Embed(
                title="Member Kicked",
                description=f"{member.mention} has been kicked.",
                color=discord.Color.red()
            )
            embed.add_field(name="Reason", value=reason or "No reason provided")
            await ctx.send(embed=embed)
        except discord.Forbidden:
            await ctx.send("I don't have permission to kick that member.")
        except Exception as e:
            logger.error(f"Error kicking member: {e}", exc_info=True)
            await ctx.send(f"An error occurred: {e}")
    
    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason=None):
        """Ban a member from the server"""
        if ctx.author.top_role <= member.top_role:
            await ctx.send("You cannot ban someone with a higher or equal role.")
            return
            
        try:
            await member.ban(reason=reason, delete_message_days=1)
            embed = discord.Embed(
                title="Member Banned",
                description=f"{member.mention} has been banned.",
                color=discord.Color.dark_red()
            )
            embed.add_field(name="Reason", value=reason or "No reason provided")
            await ctx.send(embed=embed)
        except discord.Forbidden:
            await ctx.send("I don't have permission to ban that member.")
        except Exception as e:
            logger.error(f"Error banning member: {e}", exc_info=True)
            await ctx.send(f"An error occurred: {e}")
    
    @commands.command(name="unban")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, *, user_id_or_name):
        """Unban a user from the server"""
        try:
            # Try to parse as ID first
            try:
                user_id = int(user_id_or_name)
                user = discord.Object(id=user_id)
                await ctx.guild.unban(user)
                await ctx.send(f"Unbanned user with ID {user_id}")
                return
            except ValueError:
                # Not a valid ID, try to find by name
                banned_users = [entry async for entry in ctx.guild.bans()]
                name, discriminator = user_id_or_name.split('#') if '#' in user_id_or_name else (user_id_or_name, None)
                
                for ban_entry in banned_users:
                    user = ban_entry.user
                    if discriminator:
                        if user.name == name and user.discriminator == discriminator:
                            await ctx.guild.unban(user)
                            await ctx.send(f"Unbanned {user.name}#{user.discriminator}")
                            return
                    else:
                        if user.name == name:
                            await ctx.guild.unban(user)
                            await ctx.send(f"Unbanned {user.name}#{user.discriminator}")
                            return
                
                await ctx.send(f"Could not find banned user: {user_id_or_name}")
        except discord.Forbidden:
            await ctx.send("I don't have permission to unban users.")
        except Exception as e:
            logger.error(f"Error unbanning user: {e}", exc_info=True)
            await ctx.send(f"An error occurred: {e}")
    
    @commands.command(name="slowmode")
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, seconds: int):
        """Set the slowmode delay for the current channel"""
        if seconds < 0 or seconds > 21600:
            await ctx.send("Slowmode must be between 0 and 21600 seconds (6 hours).")
            return
            
        try:
            await ctx.channel.edit(slowmode_delay=seconds)
            if seconds == 0:
                await ctx.send("Slowmode disabled for this channel.")
            else:
                await ctx.send(f"Slowmode set to {seconds} seconds for this channel.")
        except discord.Forbidden:
            await ctx.send("I don't have permission to edit this channel.")
        except Exception as e:
            logger.error(f"Error setting slowmode: {e}", exc_info=True)
            await ctx.send(f"An error occurred: {e}")
