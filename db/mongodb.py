import logging
import motor.motor_asyncio
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

logger = logging.getLogger("bot")

class MongoDB:
    """Class to handle MongoDB connection and operations"""
    
    def __init__(self, mongo_uri=None):
        self.mongo_uri = mongo_uri
        self.client = None
        self.db = None
        self.connected = False

    async def connect(self):
        """Connect to MongoDB database"""
        if not self.mongo_uri:
            logger.warning("No MongoDB URI provided. Database functionality will be disabled.")
            return False
            
        try:
            # Create a client connection to MongoDB
            logger.info("Connecting to MongoDB...")
            self.client = motor.motor_asyncio.AsyncIOMotorClient(
                self.mongo_uri, 
                serverSelectionTimeoutMS=5000
            )
            
            # Test the connection
            await self.client.admin.command('ping')
            
            # Get the database
            self.db = self.client.devportalvas
            self.connected = True
            logger.info("Successfully connected to MongoDB")
            return True
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Could not connect to MongoDB: {e}")
            self.connected = False
            return False
        except Exception as e:
            logger.error(f"Unexpected error when connecting to MongoDB: {e}", exc_info=True)
            self.connected = False
            return False

    async def close(self):
        """Close the MongoDB connection"""
        if self.client:
            self.client.close()
            self.connected = False
            logger.info("Closed MongoDB connection")

    async def get_user_settings(self, user_id):
        """Get settings for a user from the database"""
        if not self.connected:
            logger.warning("Attempted database operation without connection")
            return None
            
        try:
            collection = self.db.users
            user_data = await collection.find_one({"_id": str(user_id)})
            return user_data
        except Exception as e:
            logger.error(f"Error retrieving user settings: {e}", exc_info=True)
            return None

    async def update_user_settings(self, user_id, settings):
        """Update settings for a user in the database"""
        if not self.connected:
            logger.warning("Attempted database operation without connection")
            return False
            
        try:
            collection = self.db.users
            result = await collection.update_one(
                {"_id": str(user_id)},
                {"$set": settings},
                upsert=True
            )
            return result.acknowledged
        except Exception as e:
            logger.error(f"Error updating user settings: {e}", exc_info=True)
            return False

    async def get_guild_settings(self, guild_id):
        """Get settings for a guild from the database"""
        if not self.connected:
            logger.warning("Attempted database operation without connection")
            return None
            
        try:
            collection = self.db.guilds
            guild_data = await collection.find_one({"_id": str(guild_id)})
            return guild_data
        except Exception as e:
            logger.error(f"Error retrieving guild settings: {e}", exc_info=True)
            return None

    async def update_guild_settings(self, guild_id, settings):
        """Update settings for a guild in the database"""
        if not self.connected:
            logger.warning("Attempted database operation without connection")
            return False
            
        try:
            collection = self.db.guilds
            result = await collection.update_one(
                {"_id": str(guild_id)},
                {"$set": settings},
                upsert=True
            )
            return result.acknowledged
        except Exception as e:
            logger.error(f"Error updating guild settings: {e}", exc_info=True)
            return False
