import os
import random
import time
import logging
import traceback
import functools
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple, Union, Callable

from pymongo import MongoClient, errors
from pymongo.collection import Collection
from pymongo.database import Database
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('database')

# Configuration
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise Exception("MONGO_URI environment variable not found")

MAX_RETRIES = 5
RETRY_DELAY = 1  # seconds base delay

class QueryPerformanceTracker:
    """
    Track and analyze database query performance.
    """
    def __init__(self):
        self.query_stats = {}
        self.slow_query_threshold = 0.5  # seconds
        
    def record_query(self, collection: str, operation: str, duration: float, query_details: Optional[Dict] = None) -> None:
        """
        Record a database query for performance tracking.
        
        Args:
            collection: Collection name
            operation: Operation type (find, update, insert, etc.)
            duration: Query duration in seconds
            query_details: Optional query details for slow query analysis
        """
        key = f"{collection}.{operation}"
        
        if key not in self.query_stats:
            self.query_stats[key] = {
                "count": 0,
                "total_time": 0.0,
                "avg_time": 0.0,
                "min_time": float('inf'),
                "max_time": 0.0,
                "slow_queries": 0
            }
            
        stats = self.query_stats[key]
        stats["count"] += 1
        stats["total_time"] += duration
        stats["avg_time"] = stats["total_time"] / stats["count"]
        stats["min_time"] = min(stats["min_time"], duration)
        stats["max_time"] = max(stats["max_time"], duration)
        
        if duration > self.slow_query_threshold:
            stats["slow_queries"] += 1
            logger.warning(
                f"Slow query: {collection}.{operation} took {duration:.4f}s. "
                f"Details: {query_details or 'not provided'}"
            )
    
    def get_stats(self) -> Dict[str, Dict[str, Union[int, float]]]:
        """Get all recorded query statistics."""
        return self.query_stats
    
    def get_slow_queries(self) -> Dict[str, Dict[str, Union[int, float]]]:
        """Get statistics for slow queries only."""
        return {k: v for k, v in self.query_stats.items() if v["slow_queries"] > 0}
    
    def reset_stats(self) -> None:
        """Reset all statistics."""
        self.query_stats = {}

def with_performance_tracking(func):
    """
    Decorator to track query performance and handle retries with exponential backoff.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Get database connection from singleton
        db_conn = DatabaseConnection.get_instance()
        
        # Extract collection name from function docstring or name
        collection_name = func.__name__.split('_')[0] if '_' in func.__name__ else "unknown"
        operation = func.__name__.split('_')[-1] if '_' in func.__name__ else func.__name__
        
        # Track query time
        start_time = time.time()
        retry_count = 0
        last_exception = None
        
        while retry_count < MAX_RETRIES:
            try:
                result = func(*args, **kwargs)
                
                # Record successful query
                duration = time.time() - start_time
                db_conn.performance_tracker.record_query(
                    collection_name, 
                    operation, 
                    duration,
                    {"args": str(args), "kwargs": str(kwargs)}
                )
                
                if retry_count > 0:
                    logger.info(f"Query {func.__name__} succeeded after {retry_count} retries in {duration:.4f}s")
                    
                return result
                
            except errors.ConnectionFailure as e:
                retry_count += 1
                last_exception = e
                
                # Use exponential backoff
                wait_time = min(RETRY_DELAY * (2 ** retry_count), 30)
                
                logger.warning(
                    f"Connection failure in {func.__name__}, attempt {retry_count}/{MAX_RETRIES}. "
                    f"Retrying in {wait_time:.2f}s: {e}"
                )
                
                # Try to reconnect before next attempt
                db_conn.reconnect()
                
                time.sleep(wait_time)
                
            except errors.OperationFailure as e:
                # Non-retryable errors
                logger.error(f"Operation failure in {func.__name__}: {e}")
                
                # Record failed query
                duration = time.time() - start_time
                db_conn.performance_tracker.record_query(
                    collection_name, 
                    f"{operation}_error", 
                    duration,
                    {"error": str(e), "args": str(args), "kwargs": str(kwargs)}
                )
                
                # Record error in database
                try:
                    db_conn.errors.insert_one({
                        "type": "OperationFailure",
                        "function": func.__name__,
                        "message": str(e),
                        "args": str(args),
                        "kwargs": str(kwargs),
                        "timestamp": datetime.now()
                    })
                except Exception as log_error:
                    logger.error(f"Failed to log error: {log_error}")
                    
                raise
                
            except Exception as e:
                retry_count += 1
                last_exception = e
                
                # Use exponential backoff
                wait_time = min(RETRY_DELAY * (2 ** retry_count), 30)
                
                logger.error(
                    f"Error in {func.__name__}, attempt {retry_count}/{MAX_RETRIES}. "
                    f"Retrying in {wait_time:.2f}s: {e}"
                )
                logger.debug(traceback.format_exc())
                
                # Record error in database if possible
                try:
                    if hasattr(db_conn, 'errors') and db_conn.errors is not None:
                        db_conn.errors.insert_one({
                            "type": type(e).__name__,
                            "function": func.__name__,
                            "message": str(e),
                            "args": str(args),
                            "kwargs": str(kwargs),
                            "timestamp": datetime.now()
                        })
                except Exception as log_error:
                    logger.error(f"Failed to log error: {log_error}")
                
                if retry_count == MAX_RETRIES:
                    # Record failed query
                    duration = time.time() - start_time
                    db_conn.performance_tracker.record_query(
                        collection_name, 
                        f"{operation}_error", 
                        duration,
                        {"error": str(e), "args": str(args), "kwargs": str(kwargs)}
                    )
                    break
                    
                time.sleep(wait_time)
        
        if last_exception:
            logger.critical(f"Max retries ({MAX_RETRIES}) reached for {func.__name__}: {last_exception}")
            raise last_exception
        
    return wrapper

class DatabaseConnection:
    """
    Singleton class for MongoDB connection with enhanced error handling,
    connection pooling, and performance monitoring.
    """
    _instance = None
    
    def __init__(self):
        self.client = None
        self.db = None
        self.economies = None
        self.shop = None
        self.errors = None
        self.feedback = None
        self.server_stats = None
        
        # Performance tracking
        self.performance_tracker = QueryPerformanceTracker()
        
        # Connection status
        self.connected = False
        self.connection_start_time = None
        self.last_error = None
        self.last_error_time = None
        self.connection_attempts = 0
        
        # Always connect on initialization
        try:
            self.connect()
        except Exception as e:
            logger.error(f"Error initializing database connection: {e}")
            logger.debug(traceback.format_exc())
    
    @classmethod
    def get_instance(cls):
        """Get the singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def connect(self):
        """Connect to MongoDB with improved error handling"""
        try:
            self.connection_attempts += 1
            
            # Improved connection settings for better performance and reliability
            self.client = MongoClient(
                MONGO_URI,
                serverSelectionTimeoutMS=5000,      # 5 second timeout for server selection
                connectTimeoutMS=10000,             # 10 second timeout for initial connection
                socketTimeoutMS=45000,              # 45 second timeout for socket operations
                maxPoolSize=50,                     # Maximum connection pool size
                minPoolSize=10,                     # Minimum connection pool size
                maxIdleTimeMS=60000,               # 1 minute maximum idle time
                waitQueueTimeoutMS=5000,           # 5 second timeout for waiting in queue
                retryWrites=True,                  # Retry write operations
                retryReads=True                    # Retry read operations
            )
            
            # Test the connection
            self.client.admin.command('ping')
            
            # Initialize database and collections
            self.db = self.client['discord_economy']
            self.economies = self.db.economies
            self.shop = self.db.shop
            self.errors = self.db.errors
            self.feedback = self.db.feedback
            self.server_stats = self.db.server_stats
            
            # Create indexes for better query performance
            self._create_indexes()
            
            # Update connection status
            self.connected = True
            self.connection_start_time = datetime.now()
            self.last_error = None
            
            logger.info(f"Successfully connected to MongoDB (attempt {self.connection_attempts})")
            
            # Log connection as a server event
            self._log_server_event("connection", "Successfully connected to MongoDB", "info")
            
            return True
            
        except Exception as e:
            # Update connection status
            self.connected = False
            self.last_error = str(e)
            self.last_error_time = datetime.now()
            
            logger.error(f"Failed to connect to MongoDB (attempt {self.connection_attempts}): {e}")
            logger.debug(traceback.format_exc())
            
            # Log connection failure
            try:
                if self.client and hasattr(self, 'server_stats') and self.server_stats:
                    self._log_server_event("connection_failure", f"Failed to connect: {e}", "error")
            except Exception as log_error:
                logger.error(f"Failed to log connection failure: {log_error}")
                
            raise
    
    def reconnect(self):
        """Safely reconnect to the database"""
        logger.info("Attempting to reconnect to MongoDB...")
        
        try:
            # Safely close existing connection if it exists
            if self.client:
                try:
                    self.client.close()
                except Exception as e:
                    logger.warning(f"Error closing existing connection: {e}")
                    
            # Try to establish a new connection
            return self.connect()
            
        except Exception as e:
            logger.error(f"Failed to reconnect to MongoDB: {e}")
            logger.debug(traceback.format_exc())
            return False
    
    def _create_indexes(self):
        """Create indexes for better query performance"""
        try:
            # Economies collection - global currency system
            self.economies.create_index([("user_id", 1)], unique=True)
            
            # Shop collection - items for sale
            self.shop.create_index([("item_id", 1)], unique=True)
            
            # Feedback collection - command feedback tracking
            self.feedback.create_index([("command_name", 1)])
            self.feedback.create_index([("user_id", 1)])
            self.feedback.create_index([("timestamp", -1)])
            
            # Errors collection - error tracking
            self.errors.create_index([("timestamp", -1)])
            self.errors.create_index([("type", 1)])
            
            # Server stats collection - performance tracking
            self.server_stats.create_index([("timestamp", -1)])
            self.server_stats.create_index([("event_type", 1)])
            
            logger.info("Created database indexes for optimal query performance")
            
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
    
    def _log_server_event(self, event_type, description, level="info"):
        """Log server events to the database for monitoring"""
        try:
            if self.connected and self.server_stats:
                self.server_stats.insert_one({
                    "event_type": event_type,
                    "description": description,
                    "level": level,
                    "timestamp": datetime.now()
                })
        except Exception as e:
            logger.warning(f"Failed to log server event: {e}")
    
    def get_connection_status(self):
        """Get the current connection status details"""
        status = {
            "connected": self.connected,
            "connection_attempts": self.connection_attempts,
            "uptime": None,
            "last_error": self.last_error,
            "last_error_time": self.last_error_time,
            "performance_stats": self.performance_tracker.get_stats()
        }
        
        if self.connection_start_time:
            uptime = datetime.now() - self.connection_start_time
            status["uptime"] = str(uptime)
            
        # Add server info if connected
        if self.connected and self.client:
            try:
                server_status = self.client.admin.command("serverStatus")
                status["server_info"] = {
                    "version": server_status.get("version"),
                    "uptime": server_status.get("uptime"),
                    "connections": server_status.get("connections")
                }
            except Exception as e:
                logger.warning(f"Failed to get server status: {e}")
                
        return status

# Create global database connection instance
db_connection = DatabaseConnection.get_instance()
db = db_connection

#
# Enhanced database functions with performance tracking and error handling
#

@with_performance_tracking
def get_balance(user_id):
    """
    Get a user's balance with enhanced error handling and performance tracking.
    
    Args:
        user_id: The user's Discord ID
        
    Returns:
        Dict containing user's balance information
    """
    try:
        # Convert user_id to string for consistency
        user_id = str(user_id)
        
        # Query database for user balance
        query = {"user_id": user_id}
        user_data = db.economies.find_one(query)
        
        # Create default balance if not found
        if not user_data:
            user_data = {
                "user_id": user_id,
                "pocket": 0,
                "bank": 0,
                "bank_limit": 10000,  # Default bank limit
                "luck": 1.0,          # Default luck multiplier for steal/heist
                "inventory": []       # User's inventory
            }
            
            # Insert new user data
            db.economies.insert_one(user_data)
            
            # Log new user creation
            logger.info(f"Created new balance for user {user_id}")
            
        return user_data
        
    except Exception as e:
        logger.error(f"Error in get_balance for user {user_id}: {e}")
        raise

@with_performance_tracking
def update_balance(user_id, amount, location="pocket"):
    """
    Update a user's balance with enhanced error handling and performance tracking.
    
    Args:
        user_id: The user's Discord ID
        amount: Amount to add (positive) or subtract (negative)
        location: Where to update balance ("pocket" or "bank")
        
    Returns:
        Dict containing updated balance information
    """
    try:
        # Convert user_id to string for consistency
        user_id = str(user_id)
        
        # Get current balance
        user_data = get_balance(user_id)
        
        # Calculate new balance
        if location == "pocket":
            new_balance = max(0, user_data.get("pocket", 0) + amount)
            update_field = "pocket"
        elif location == "bank":
            # Check bank limit
            bank_limit = user_data.get("bank_limit", 10000)
            new_balance = min(bank_limit, max(0, user_data.get("bank", 0) + amount))
            update_field = "bank"
        else:
            raise ValueError(f"Invalid location: {location}")
            
        # Update database
        db.economies.update_one(
            {"user_id": user_id},
            {"$set": {update_field: new_balance}},
            upsert=True
        )
        
        # Get updated user data
        updated_data = get_balance(user_id)
        
        # Log significant transactions
        if abs(amount) >= 10000:
            logger.info(f"Large transaction for user {user_id}: {amount} to {location}")
            
        return updated_data
        
    except Exception as e:
        logger.error(f"Error in update_balance for user {user_id}, amount {amount}, location {location}: {e}")
        raise

@with_performance_tracking
def save_balance(user_id, balance_data):
    """
    Save complete balance data for a user.
    
    Args:
        user_id: The user's Discord ID
        balance_data: Dict containing full balance data to save
        
    Returns:
        Dict containing updated balance information
    """
    try:
        # Convert user_id to string for consistency
        user_id = str(user_id)
        
        # Ensure user_id is set correctly in data
        balance_data["user_id"] = user_id
        
        # Use replace_one with upsert to replace whole document
        result = db.economies.replace_one(
            {"user_id": user_id},
            balance_data,
            upsert=True
        )
        
        # Log operation
        if result.upserted_id:
            logger.info(f"Created new balance for user {user_id}")
        else:
            logger.info(f"Updated balance for user {user_id}")
            
        return balance_data
        
    except Exception as e:
        logger.error(f"Error in save_balance for user {user_id}: {e}")
        raise

@with_performance_tracking
def update_bank_limit(user_id, new_limit):
    """
    Update a user's bank limit.
    
    Args:
        user_id: The user's Discord ID
        new_limit: New bank limit
        
    Returns:
        Dict containing updated balance information
    """
    try:
        # Convert user_id to string for consistency
        user_id = str(user_id)
        
        # Update database
        db.economies.update_one(
            {"user_id": user_id},
            {"$set": {"bank_limit": new_limit}},
            upsert=True
        )
        
        # Get updated user data
        updated_data = get_balance(user_id)
        
        # Log bank limit increase
        logger.info(f"Updated bank limit for user {user_id} to {new_limit}")
        
        return updated_data
        
    except Exception as e:
        logger.error(f"Error in update_bank_limit for user {user_id}, new limit {new_limit}: {e}")
        raise

@with_performance_tracking
def update_luck(user_id, new_luck):
    """
    Update a user's luck multiplier.
    
    Args:
        user_id: The user's Discord ID
        new_luck: New luck multiplier
        
    Returns:
        Dict containing updated balance information
    """
    try:
        # Convert user_id to string for consistency
        user_id = str(user_id)
        
        # Update database
        db.economies.update_one(
            {"user_id": user_id},
            {"$set": {"luck": new_luck}},
            upsert=True
        )
        
        # Get updated user data
        updated_data = get_balance(user_id)
        
        # Log luck multiplier change
        logger.info(f"Updated luck multiplier for user {user_id} to {new_luck}")
        
        return updated_data
        
    except Exception as e:
        logger.error(f"Error in update_luck for user {user_id}, new luck {new_luck}: {e}")
        raise

@with_performance_tracking
def add_to_inventory(user_id, item):
    """
    Add an item to user's inventory.
    
    Args:
        user_id: The user's Discord ID
        item: Item object to add to inventory
        
    Returns:
        Dict containing updated inventory
    """
    try:
        # Convert user_id to string for consistency
        user_id = str(user_id)
        
        # Get current user data
        user_data = get_balance(user_id)
        
        # Add timestamp to item
        item["acquired_at"] = datetime.now().isoformat()
        
        # Update inventory
        db.economies.update_one(
            {"user_id": user_id},
            {"$push": {"inventory": item}},
            upsert=True
        )
        
        # Get updated user data
        updated_data = get_balance(user_id)
        
        # Log item acquisition
        logger.info(f"Added item {item.get('item_id')} to inventory for user {user_id}")
        
        return updated_data
        
    except Exception as e:
        logger.error(f"Error in add_to_inventory for user {user_id}, item {item}: {e}")
        raise

@with_performance_tracking
def get_shop_items():
    """
    Get all items available in the shop with enhanced caching.
    
    Returns:
        List of shop items
    """
    try:
        # Query database for all shop items
        cursor = db.shop.find({})
        shop_items = list(cursor)
        
        # If shop is empty, create default items
        if not shop_items:
            # Default shop items
            default_items = [
                {
                    "item_id": "bank_note",
                    "name": "Bank Note",
                    "description": "Increases your bank limit by 5,000",
                    "price": 10000,
                    "stock": 100,
                    "category": "utility",
                    "effect": "bank_limit_increase",
                    "effect_value": 5000
                },
                {
                    "item_id": "luck_boost",
                    "name": "Luck Boost",
                    "description": "Increases your luck in gambling and heists by 20%",
                    "price": 25000,
                    "stock": 20,
                    "category": "booster",
                    "effect": "luck_increase",
                    "effect_value": 1.2
                },
                {
                    "item_id": "theft_shield",
                    "name": "Theft Shield",
                    "description": "Protects you from theft for 1 day",
                    "price": 100000,
                    "stock": 10,
                    "category": "protection",
                    "effect": "theft_protection",
                    "effect_value": 86400  # 24 hours in seconds
                }
            ]
            
            # Insert default items
            db.shop.insert_many(default_items)
            
            # Log shop initialization
            logger.info(f"Initialized shop with {len(default_items)} default items")
            
            return default_items
        
        return shop_items
        
    except Exception as e:
        logger.error(f"Error in get_shop_items: {e}")
        raise

@with_performance_tracking
def update_item_stock(item_id, change):
    """
    Update the stock of an item in the shop.
    
    Args:
        item_id: ID of the item
        change: Change in stock (positive to add, negative to subtract)
        
    Returns:
        Updated item data
    """
    try:
        # Get current item data
        item = db.shop.find_one({"item_id": item_id})
        
        if not item:
            raise ValueError(f"Item not found: {item_id}")
        
        # Calculate new stock (prevent negative stock)
        new_stock = max(0, item.get("stock", 0) + change)
        
        # Special case: prevent rare items from going out of stock
        if new_stock < 5 and item_id in ["bank_note", "luck_boost", "theft_shield"]:
            new_stock = 5
            logger.info(f"Preventing {item_id} from going out of stock, setting to minimum 5")
        
        # Update stock
        db.shop.update_one(
            {"item_id": item_id},
            {"$set": {"stock": new_stock}}
        )
        
        # Get updated item
        updated_item = db.shop.find_one({"item_id": item_id})
        
        # Log stock update for monitoring
        logger.info(f"Updated stock for {item_id}: {item.get('stock', 0)} -> {new_stock} (change: {change})")
        
        return updated_item
        
    except Exception as e:
        logger.error(f"Error in update_item_stock for item {item_id}, change {change}: {e}")
        raise

@with_performance_tracking
def refresh_shop_inventory():
    """
    Refresh shop inventory with randomized stock levels.
    Called periodically to reset shop.
    
    Returns:
        Dict with refresh status and updated items
    """
    try:
        # Get all shop items
        items = get_shop_items()
        updated_items = []
        
        # Update each item with random stock
        for item in items:
            item_id = item["item_id"]
            
            # Generate random stock based on item rarity
            if item_id == "bank_note":
                new_stock = random.randint(50, 100)
            elif item_id == "luck_boost":
                new_stock = random.randint(20, 50)
            elif item_id == "theft_shield":
                new_stock = random.randint(10, 25)
            else:
                new_stock = random.randint(5, 30)
            
            # Update stock
            db.shop.update_one(
                {"item_id": item_id},
                {"$set": {"stock": new_stock}}
            )
            
            # Get updated item
            updated_item = db.shop.find_one({"item_id": item_id})
            updated_items.append(updated_item)
        
        # Log shop refresh
        logger.info(f"Refreshed shop inventory with {len(updated_items)} items")
        
        # Record shop refresh in server stats
        db_connection._log_server_event("shop_refresh", f"Refreshed {len(updated_items)} shop items", "info")
        
        return {
            "status": "success",
            "items_updated": len(updated_items),
            "items": updated_items
        }
        
    except Exception as e:
        logger.error(f"Error in refresh_shop_inventory: {e}")
        
        # Record failed refresh in server stats
        db_connection._log_server_event("shop_refresh_failed", f"Failed to refresh shop: {e}", "error")
        
        raise

@with_performance_tracking
def record_feedback(user_id, command_name, feedback_type):
    """
    Record user feedback for a command.
    
    Args:
        user_id: The user's Discord ID
        command_name: Name of the command
        feedback_type: Type of feedback ('positive' or 'negative')
    
    Returns:
        Inserted feedback document
    """
    try:
        # Convert user_id to string for consistency
        user_id = str(user_id)
        
        # Create feedback document
        feedback_doc = {
            "user_id": user_id,
            "command_name": command_name,
            "feedback_type": feedback_type,
            "timestamp": datetime.now()
        }
        
        # Insert feedback
        result = db.feedback.insert_one(feedback_doc)
        feedback_doc["_id"] = result.inserted_id
        
        logger.info(f"Recorded {feedback_type} feedback for {command_name} from user {user_id}")
        
        return feedback_doc
        
    except Exception as e:
        logger.error(f"Error recording feedback for command {command_name}, user {user_id}: {e}")
        raise

@with_performance_tracking
def get_feedback_stats(command_name=None):
    """
    Get feedback statistics for commands.
    
    Args:
        command_name: Optional command name to filter stats
        
    Returns:
        Dict containing feedback statistics
    """
    try:
        pipeline = []
        
        # Filter by command if specified
        if command_name:
            pipeline.append({"$match": {"command_name": command_name}})
        
        # Group by command and feedback type
        pipeline.append({
            "$group": {
                "_id": {
                    "command": "$command_name",
                    "feedback_type": "$feedback_type"
                },
                "count": {"$sum": 1}
            }
        })
        
        # Group by command to get total and calculate percentages
        pipeline.append({
            "$group": {
                "_id": "$_id.command",
                "feedback": {
                    "$push": {
                        "type": "$_id.feedback_type",
                        "count": "$count"
                    }
                },
                "total": {"$sum": "$count"}
            }
        })
        
        # Execute aggregation
        cursor = db.feedback.aggregate(pipeline)
        results = list(cursor)
        
        # Process results to calculate percentages
        stats = {}
        for result in results:
            command = result["_id"]
            total = result["total"]
            
            # Initialize command stats
            stats[command] = {
                "total": total,
                "positive": 0,
                "negative": 0,
                "positive_percent": 0,
                "negative_percent": 0
            }
            
            # Update with actual counts
            for feedback in result["feedback"]:
                feedback_type = feedback["type"]
                count = feedback["count"]
                
                stats[command][feedback_type] = count
                stats[command][f"{feedback_type}_percent"] = round((count / total) * 100, 2)
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting feedback stats for command {command_name}: {e}")
        raise

@with_performance_tracking
def log_error(error_type, function, message, details=None):
    """
    Log an error to the database for monitoring.
    
    Args:
        error_type: Type of error
        function: Function where error occurred
        message: Error message
        details: Additional error details
    
    Returns:
        Inserted error document
    """
    try:
        # Create error document
        error_doc = {
            "type": error_type,
            "function": function,
            "message": message,
            "details": details,
            "timestamp": datetime.now(),
            "severity": "error"
        }
        
        # Insert error
        result = db.errors.insert_one(error_doc)
        error_doc["_id"] = result.inserted_id
        
        logger.error(f"Logged error: {error_type} in {function}: {message}")
        
        return error_doc
        
    except Exception as e:
        logger.error(f"Error logging error: {e}")
        # Don't raise here to prevent error cascade
        return None

@with_performance_tracking
def get_error_logs(limit=100, severity=None, error_type=None):
    """
    Get error logs from the database.
    
    Args:
        limit: Maximum number of errors to return
        severity: Optional severity to filter by
        error_type: Optional error type to filter by
        
    Returns:
        List of error documents
    """
    try:
        # Build query
        query = {}
        if severity:
            query["severity"] = severity
        if error_type:
            query["type"] = error_type
        
        # Execute query
        cursor = db.errors.find(query).sort("timestamp", -1).limit(limit)
        errors = list(cursor)
        
        return errors
        
    except Exception as e:
        logger.error(f"Error getting error logs: {e}")
        raise

@with_performance_tracking
def get_server_stats(event_type=None, limit=100):
    """
    Get server stats from the database.
    
    Args:
        event_type: Optional event type to filter by
        limit: Maximum number of events to return
        
    Returns:
        List of server stat documents
    """
    try:
        # Build query
        query = {}
        if event_type:
            query["event_type"] = event_type
        
        # Execute query
        cursor = db.server_stats.find(query).sort("timestamp", -1).limit(limit)
        stats = list(cursor)
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting server stats: {e}")
        raise

@with_performance_tracking
def get_db_metrics():
    """
    Get database metrics for monitoring.
    
    Returns:
        Dict containing database metrics
    """
    try:
        metrics = {
            "collections": {},
            "performance": db_connection.performance_tracker.get_stats(),
            "connection_status": db_connection.get_connection_status(),
            "slow_queries": db_connection.performance_tracker.get_slow_queries()
        }
        
        # Get collection stats
        for collection_name in ["economies", "shop", "errors", "feedback", "server_stats"]:
            try:
                # Skip if collection doesn't exist
                if collection_name not in db.db.list_collection_names():
                    continue
                    
                collection = getattr(db, collection_name)
                count = collection.count_documents({})
                metrics["collections"][collection_name] = {
                    "count": count
                }
            except Exception as coll_error:
                logger.warning(f"Error getting stats for collection {collection_name}: {coll_error}")
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting database metrics: {e}")
        raise