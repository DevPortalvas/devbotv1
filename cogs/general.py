import discord
from discord.ext import commands
import logging
import platform
import time
from datetime import datetime

logger = logging.getLogger("bot")

class General(commands.Cog):
    """General commands for the bot"""
    
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.utcnow()
    
    @commands.command(name="ping")
    async def ping(self, ctx):
        """Check the bot's latency"""
        start_time = time.time()
        message = await ctx.send("Pinging...")
        end_time = time.time()
        
        api_latency = round(self.bot.latency * 1000)
        bot_latency = round((end_time - start_time) * 1000)
        
        embed = discord.Embed(title="🏓 Pong!", color=discord.Color.green())
        embed.add_field(name="API Latency", value=f"{api_latency}ms", inline=True)
        embed.add_field(name="Bot Latency", value=f"{bot_latency}ms", inline=True)
        
        await message.edit(content=None, embed=embed)
    
    @commands.command(name="help")
    async def help_command(self, ctx, command=None):
        """Shows help information for commands"""
        if command is None:
            # General help menu
            embed = discord.Embed(
                title="Bot Commands",
                description="Here are all the available commands. Use `!help <command>` for more details.",
                color=discord.Color.blue()
            )
            
            # Group commands by cog
            for cog_name, cog in self.bot.cogs.items():
                command_list = [f"`{cmd.name}`" for cmd in cog.get_commands() if not cmd.hidden]
                if command_list:
                    embed.add_field(name=cog_name, value=", ".join(command_list), inline=False)
                    
            embed.set_footer(text=f"Type !help <command> for more details on a command.")
            await ctx.send(embed=embed)
        else:
            # Specific command help
            cmd = self.bot.get_command(command)
            if cmd is None:
                await ctx.send(f"I couldn't find a command called `{command}`.")
                return
                
            embed = discord.Embed(
                title=f"Command: {cmd.name}",
                description=cmd.help or "No description available.",
                color=discord.Color.blue()
            )
            
            if cmd.aliases:
                embed.add_field(name="Aliases", value=", ".join([f"`{alias}`" for alias in cmd.aliases]), inline=False)
                
            if cmd.signature:
                embed.add_field(name="Usage", value=f"`!{cmd.name} {cmd.signature}`", inline=False)
            else:
                embed.add_field(name="Usage", value=f"`!{cmd.name}`", inline=False)
                
            await ctx.send(embed=embed)
    
    @commands.command(name="info")
    async def info(self, ctx):
        """Get information about the bot"""
        embed = discord.Embed(
            title="Bot Information",
            description="DevPortalvas Discord Bot",
            color=discord.Color.blue()
        )
        
        # Calculate uptime
        uptime = datetime.utcnow() - self.start_time
        uptime_str = str(uptime).split('.')[0]  # Remove microseconds
        
        # Add bot information
        embed.add_field(name="Version", value=self.bot.version, inline=True)
        embed.add_field(name="Uptime", value=uptime_str, inline=True)
        embed.add_field(name="Discord.py", value=discord.__version__, inline=True)
        embed.add_field(name="Python", value=platform.python_version(), inline=True)
        embed.add_field(name="Servers", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="Users", value=str(len(set(self.bot.get_all_members()))), inline=True)
        
        embed.set_footer(text=f"Bot ID: {self.bot.user.id}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="invite")
    async def invite(self, ctx):
        """Get an invite link for the bot"""
        # Create an oauth2 URL with basic permissions
        permissions = discord.Permissions(
            send_messages=True,
            embed_links=True,
            attach_files=True,
            read_messages=True,
            read_message_history=True,
            add_reactions=True
        )
        
        invite_url = discord.utils.oauth_url(
            client_id=str(self.bot.user.id),
            permissions=permissions
        )
        
        embed = discord.Embed(
            title="Invite Link",
            description=f"Click the link below to add me to your server:\n\n{invite_url}",
            color=discord.Color.blue()
        )
        
        await ctx.send(embed=embed)
