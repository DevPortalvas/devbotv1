import os
import discord
import aiohttp
from discord.ext import commands
from dotenv import load_dotenv
from utils.database import DatabaseConnection
from utils.webhook import WebhookManager
from pymongo import MongoClient

load_dotenv()
TOKEN = os.getenv("TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class ExtendedBot(commands.Bot):
    """Custom Bot class with additional properties for webhook and session"""
    def __init__(self, command_prefix, **kwargs):
        super().__init__(command_prefix, **kwargs)
        self.webhook_manager = None
        self.session = None

# Connect to MongoDB
try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo_client.server_info()  # Test connection
    db = mongo_client['discord_economy']  # Use the database name explicitly
    print("Connected to MongoDB successfully")
except Exception as e:
    print(f"Failed to connect to MongoDB: {e}")
    db = None

async def get_prefix(bot, message):
    try:
        if not message.guild:
            return "d!"  # Use default prefix in DMs too

        # Get prefix from MongoDB
        prefix_data = db.prefixes.find_one({"guild_id": str(message.guild.id)})
        return prefix_data["prefix"] if prefix_data else "d!"
    except Exception:
        return "d!"  # Default fallback

# Create the bot with our extended class
bot = ExtendedBot(command_prefix=get_prefix, 
                 intents=intents, 
                 help_command=None)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    
    # Set streaming activity
    activity = discord.Game(name="Discord Economy")
    await bot.change_presence(activity=activity)
    
    # Initialize webhook status manager
    bot.session = aiohttp.ClientSession()
    webhook_url = os.getenv("STATUS_WEBHOOK_URL")
    if webhook_url:
        db_connection = DatabaseConnection.get_instance()
        bot.webhook_manager = WebhookManager(webhook_url, bot, db_connection)
        await bot.webhook_manager.initialize()
        bot.loop.create_task(bot.webhook_manager.update_status())

    # Load all extensions from /commands and subfolders
    for root, dirs, files in os.walk("./commands"):
        for filename in files:
            if filename.endswith(".py"):
                try:
                    path = os.path.join(root, filename)
                    module_path = path.replace("./", "").replace("/", ".")[:-3]
                    
                    # Skip loading tester modules as requested
                    if module_path.startswith("commands.tester"):
                        continue
                        
                    await bot.load_extension(module_path)
                    print(f"Loaded {filename}")
                except Exception as e:
                    print(f"Failed to load {filename}: {e}")

    # Sync slash commands only once
    try:
        synced = await bot.tree.sync()
        print(f"Successfully synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"Failed to sync slash commands: {e}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if bot.user in message.mentions:
        prefix = await get_prefix(bot, message)
        embed = discord.Embed(
            title="Server Prefix",
            description=f"My prefix in this server is `{prefix}`",
            color=discord.Color.blue()
        )
        await message.channel.send(embed=embed)

    await bot.process_commands(message)

def run_bot():
    # Check if TOKEN is available
    if not TOKEN:
        print("ERROR: Discord bot token not found. Please set TOKEN in .env file.")
        return

    # Register bot with web dashboard if available
    try:
        from app import set_bot_instance
        set_bot_instance(bot)
        print("Registered bot with dashboard")
    except ImportError:
        print("Dashboard not available, running in bot-only mode")

    # Add instance locking to prevent multiple bots running at once
    import socket
    import sys

    # Try to acquire a lock unless running in a Render worker
    if not os.environ.get('RENDER_SERVICE_TYPE') == 'worker':
        # Create a socket to serve as a lock
        lock_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Try to bind to a local port that will serve as our lock
            lock_socket.bind(('localhost', 9876))
            print("Bot instance lock acquired - running as primary instance")
        except socket.error:
            print("Another instance is already running - exiting")
            sys.exit(0)

    try:
        bot.run(TOKEN)
    finally:
        if bot.webhook_manager:
            bot.loop.run_until_complete(bot.webhook_manager.set_offline())
        if bot.session:
            bot.loop.run_until_complete(bot.session.close())

if __name__ == "__main__":
    run_bot()