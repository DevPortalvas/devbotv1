import os
import logging
import discord
from discord.ext import commands
import asyncio
import importlib
import pkgutil

from db.mongodb import MongoDB

logger = logging.getLogger("bot")

class DevBotClient(commands.Bot):
    """Main bot class for the DevPortalvas Discord Bot"""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix=commands.when_mentioned_or('!'),
            intents=intents,
            help_command=None
        )
        
        # Initialize database connection
        mongo_uri = os.getenv("MONGO_URI")
        self.db = MongoDB(mongo_uri)
        
        # Bot configuration
        self.version = "3.0.0"
        self.activity = discord.Activity(
            type=discord.ActivityType.listening, 
            name="commands | !help"
        )

    async def setup_hook(self):
        """Hook that is called when the bot is starting up"""
        logger.info("Setting up bot...")
        
        # Connect to MongoDB
        await self.db.connect()
        
        # Load all cogs
        await self.load_cogs()

    async def load_cogs(self):
        """Automatically load all cogs from the cogs package"""
        logger.info("Loading cogs...")
        
        # Find all modules in the cogs package
        cogs_package = 'cogs'
        for _, name, ispkg in pkgutil.iter_modules([cogs_package]):
            if not ispkg:
                try:
                    # Import and load the cog
                    module = importlib.import_module(f"{cogs_package}.{name}")
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if isinstance(attr, type) and issubclass(attr, commands.Cog) and attr is not commands.Cog:
                            await self.add_cog(attr(self))
                            logger.info(f"Loaded cog: {attr.__name__}")
                except Exception as e:
                    logger.error(f"Failed to load cog {name}: {e}", exc_info=True)

    async def on_ready(self):
        """Event called when the bot is ready"""
        logger.info(f"Bot connected as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        
        # Set bot activity
        await self.change_presence(activity=self.activity)

    async def on_command_error(self, ctx, error):
        """Global error handler for commands"""
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing required argument: {error.param.name}")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"Bad argument: {error}")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have permission to use this command.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send(f"I don't have the necessary permissions to execute this command: {error}")
        else:
            logger.error(f"Command error: {error}", exc_info=True)
            await ctx.send(f"An error occurred: {error}")

    async def on_message(self, message):
        """Event called when a message is received"""
        # Ignore messages from bots
        if message.author.bot:
            return
            
        # Process commands
        await self.process_commands(message)
