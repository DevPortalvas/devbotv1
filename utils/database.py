
import os
from pymongo import MongoClient, errors
from dotenv import load_dotenv
import time
from functools import wraps

load_dotenv()

# Connect to MongoDB
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise Exception("MONGO_URI environment variable not found")

MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

def with_retry(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except errors.ConnectionFailure as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                time.sleep(RETRY_DELAY * (attempt + 1))
        return None
    return wrapper

class DatabaseConnection:
    _instance = None
    
    def __init__(self):
        self.client = None
        self.db = None
        self.connect()
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def connect(self):
        try:
            self.client = MongoClient(MONGO_URI)
            self.db = self.client['discord_economy']
            # Test the connection
            self.client.admin.command('ping')
        except Exception as e:
            print(f"Failed to connect to database: {e}")
            raise

    def reconnect(self):
        if self.client:
            self.client.close()
        self.connect()

db_connection = DatabaseConnection.get_instance()
db = db_connection.db

@with_retry
def get_balance(guild_id, user_id):
    try:
        query = {"guild_id": str(guild_id), "user_id": str(user_id)}
        user_data = db.economies.find_one(query)
        
        if not user_data:
            user_data = {
                "guild_id": str(guild_id),
                "user_id": str(user_id),
                "pocket": 0,
                "bank": 0
            }
            db.economies.insert_one(user_data)
            return {"pocket": 0, "bank": 0}
        
        return {
            "pocket": user_data.get("pocket", 0),
            "bank": user_data.get("bank", 0)
        }
    except Exception as e:
        print(f"Database error in get_balance: {e}")
        raise

@with_retry
def update_balance(guild_id, user_id, amount, location="pocket"):
    MAX_VALUE = 2**63-1
    query = {"guild_id": str(guild_id), "user_id": str(user_id)}
    
    current = db.economies.find_one(query)
    if current is None:
        current = {location: 0}
    
    new_amount = min(MAX_VALUE, max(0, current.get(location, 0) + amount))
    update = {"$set": {location: new_amount}}
    db.economies.update_one(query, update, upsert=True)

@with_retry
def save_balance(guild_id, user_id, balance):
    query = {"guild_id": str(guild_id), "user_id": str(user_id)}
    update = {"$set": balance}
    db.economies.update_one(query, update, upsert=True)
