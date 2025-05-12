import os
import asyncio
import logging
from dotenv import load_dotenv

from bot import DevBotClient
from utils.logger import setup_logging

# Load environment variables
load_dotenv()

# Setup logging
setup_logging()
logger = logging.getLogger("bot")

async def main():
    # Get configuration from environment variables
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        logger.critical("No Discord token found. Please set the DISCORD_TOKEN environment variable.")
        return

    # Create and run the bot
    bot = DevBotClient()
    
    try:
        logger.info("Starting bot...")
        await bot.start(token)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt. Shutting down...")
        await bot.close()
    except Exception as e:
        logger.error(f"Error during bot execution: {e}", exc_info=True)
        await bot.close()

if __name__ == "__main__":
    asyncio.run(main())
