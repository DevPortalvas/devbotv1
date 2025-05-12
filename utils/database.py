
import os
import random
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
        self.economies = None
        self.shop = None
        # Always connect on initialization
        try:
            self.connect()
        except Exception as e:
            print(f"Error initializing database connection: {e}")
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def connect(self):
        try:
            self.client = MongoClient(MONGO_URI)
            self.db = self.client['discord_economy']
            # Initialize collection references
            self.economies = self.db.economies
            self.shop = self.db.shop
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
db = db_connection

@with_retry
def get_balance(guild_id, user_id):
    try:
        # Get a fresh db connection
        db_conn = DatabaseConnection.get_instance()
        
        # Global currency - only use user_id
        query = {"user_id": str(user_id)}
        user_data = db_conn.economies.find_one(query)
        
        if not user_data:
            user_data = {
                "user_id": str(user_id),
                "pocket": 0,
                "bank": 0,
                "bank_limit": 10000,  # Default bank limit
                "luck": 1.0,          # Default luck multiplier for steal/heist
                "inventory": []       # User's inventory of purchased items
            }
            db_conn.economies.insert_one(user_data)
            return {"pocket": 0, "bank": 0, "bank_limit": 10000, "luck": 1.0, "inventory": []}
        
        return {
            "pocket": user_data.get("pocket", 0),
            "bank": user_data.get("bank", 0),
            "bank_limit": user_data.get("bank_limit", 10000),
            "luck": user_data.get("luck", 1.0),
            "inventory": user_data.get("inventory", [])
        }
    except Exception as e:
        print(f"Database error in get_balance: {e}")
        raise

@with_retry
def update_balance(guild_id, user_id, amount, location="pocket"):
    # Get a fresh db connection
    db_conn = DatabaseConnection.get_instance()
    
    MAX_VALUE = 2**63-1
    # Global currency - only use user_id
    query = {"user_id": str(user_id)}
    
    current = db_conn.economies.find_one(query)
    if current is None:
        current = {
            "pocket": 0,
            "bank": 0,
            "bank_limit": 10000,
            "luck": 1.0,
            "inventory": []
        }
    
    # If depositing to bank, ensure it doesn't exceed the limit
    if location == "bank":
        bank_limit = current.get("bank_limit", 10000)
        current_bank = current.get("bank", 0)
        
        # Limit how much can be added based on bank limit
        if amount > 0:
            amount = min(amount, bank_limit - current_bank)
            if amount <= 0:  # Bank is full
                return False
    
    new_amount = min(MAX_VALUE, max(0, current.get(location, 0) + amount))
    update = {"$set": {location: new_amount}}
    db_conn.economies.update_one(query, update, upsert=True)
    return True

@with_retry
def save_balance(guild_id, user_id, balance):
    # Get a fresh db connection
    db_conn = DatabaseConnection.get_instance()
    
    # Global currency - only use user_id
    query = {"user_id": str(user_id)}
    update = {"$set": balance}
    db_conn.economies.update_one(query, update, upsert=True)
    
@with_retry
def update_bank_limit(user_id, new_limit):
    # Get a fresh db connection
    db_conn = DatabaseConnection.get_instance()
    
    query = {"user_id": str(user_id)}
    update = {"$set": {"bank_limit": new_limit}}
    db_conn.economies.update_one(query, update, upsert=True)
    
@with_retry
def update_luck(user_id, new_luck):
    # Get a fresh db connection
    db_conn = DatabaseConnection.get_instance()
    
    query = {"user_id": str(user_id)}
    update = {"$set": {"luck": new_luck}}
    db_conn.economies.update_one(query, update, upsert=True)
    
@with_retry
def add_to_inventory(user_id, item):
    # Get a fresh db connection
    db_conn = DatabaseConnection.get_instance()
    
    query = {"user_id": str(user_id)}
    update = {"$push": {"inventory": item}}
    db_conn.economies.update_one(query, update, upsert=True)
    
@with_retry
def get_shop_items():
    # Get a fresh db connection
    db_conn = DatabaseConnection.get_instance()
    
    # Get the current shop items with stock
    shop_data = db_conn.shop.find_one({"id": "current_shop"})
    
    if not shop_data or time.time() - shop_data.get("last_reset", 0) > 10800:  # 3 hours in seconds
        # Time to reset the shop
        items = [
            # Always included items with minimum stock of 5
            {"id": "banknote", "name": "🏦 Bank Note", "price": 5000, "description": "Increases your bank limit by $5,000", "stock": random.randint(5, 10)},
            {"id": "luck_boost", "name": "🍀 Luck Boost", "price": 7500, "description": "Increases your luck by 10% for steal and heist commands", "stock": random.randint(5, 8)},
            {"id": "shield", "name": "🛡️ Theft Shield", "price": 100000, "description": "Protects your money from theft for 24 hours", "stock": random.randint(5, 7)},
            
            # Optional items
            {"id": "medal", "name": "🥇 Prestige Medal", "price": 50000, "description": "A rare collectible to show your wealth", "stock": random.randint(0, 3)},
            {"id": "mystery_box", "name": "📦 Mystery Box", "price": 15000, "description": "Contains a random reward", "stock": random.randint(3, 8)}
        ]
        
        # The first 3 items are guaranteed to be in stock (bank notes, luck boost, shield)
        guaranteed_items = items[:3]
        
        # For the remaining items, randomly determine if they'll be in stock
        optional_items = []
        for item in items[3:]:
            if random.random() > 0.3:  # 70% chance to include each optional item
                optional_items.append(item)
        
        # Combine guaranteed and optional items
        available_items = guaranteed_items + optional_items
        
        # Save to database
        db_conn.shop.update_one(
            {"id": "current_shop"}, 
            {"$set": {"items": available_items, "last_reset": time.time()}}, 
            upsert=True
        )
        
        return available_items
    
    return shop_data.get("items", [])
    
@with_retry
def update_item_stock(item_id, change):
    # Get a fresh db connection
    db_conn = DatabaseConnection.get_instance()
    
    shop_data = db_conn.shop.find_one({"id": "current_shop"})
    if not shop_data:
        return False
        
    items = shop_data.get("items", [])
    for item in items:
        if item["id"] == item_id:
            new_stock = item["stock"] + change
            if new_stock < 0:
                return False
                
            item["stock"] = new_stock
            db_conn.shop.update_one({"id": "current_shop"}, {"$set": {"items": items}})
            return True
            
    return False
