import os
import logging
import json
import psutil
import discord
from datetime import datetime, timedelta
from functools import wraps
from pymongo import MongoClient

from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-key-replace-in-production")

# Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI")
try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo_client.server_info()  # Test connection
    db = mongo_client['discord_economy']  # Use the database name explicitly
    
    # Force access to a collection to validate connection further
    test_collection = db.list_collection_names()
    logger.info(f"Connected to MongoDB successfully. Collections: {test_collection}")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    db = None

# Sample admin user - in production, use a proper database
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "password")
OWNER_ID = "545609811354583040"  # Discord ID of the owner

# Import bot instance from main.py to access bot data
try:
    from main import bot
except ImportError:
    logger.warning("Could not import bot from main.py")
    bot = None

# Sample user for admin access
class User(UserMixin):
    def __init__(self, id, username, is_admin=False):
        self.id = id
        self.username = username
        self.is_admin = is_admin

# Function to get real error logs from database
def get_error_logs():
    try:
        if db is not None and 'error_logs' in db.list_collection_names():
            errors = list(db.error_logs.find().sort('timestamp', -1).limit(50))
            return [
                {
                    "id": str(err.get('_id', f"ERR-{i}")),
                    "timestamp": err.get('timestamp', datetime.now()).strftime("%Y-%m-%d %H:%M:%S") 
                                if isinstance(err.get('timestamp'), datetime) else str(err.get('timestamp', '')),
                    "type": err.get('error_type', 'Unknown'),
                    "type_badge": "bg-danger" if err.get('severity') == 'critical' else 
                                 "bg-warning" if err.get('severity') == 'warning' else "bg-info",
                    "severity": err.get('severity', 'Error').title(),
                    "severity_badge": "bg-danger" if err.get('severity') == 'critical' else 
                                     "bg-warning" if err.get('severity') == 'warning' else "bg-info",
                    "message": err.get('message', 'Unknown error'),
                    "location": err.get('function', 'Unknown location')
                } for i, err in enumerate(errors)
            ]
        else:
            # Initialize with a startup log if no errors in database
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return [
                {
                    "id": "EVT-001",
                    "timestamp": current_time,
                    "type": "System",
                    "type_badge": "bg-success",
                    "severity": "Info",
                    "severity_badge": "bg-success",
                    "message": "Dashboard initialized successfully",
                    "location": "app.py in get_error_logs()"
                }
            ]
    except Exception as e:
        logger.error(f"Error fetching error logs: {e}")
        # Fallback to default log on error
        return [
            {
                "id": "ERR-DASH",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "type": "Dashboard",
                "type_badge": "bg-danger",
                "severity": "Error",
                "severity_badge": "bg-danger",
                "message": f"Could not retrieve error logs: {str(e)}",
                "location": "app.py in get_error_logs()"
            }
        ]

# Get real system events
def get_system_events():
    try:
        if db is not None and 'system_events' in db.list_collection_names():
            events = list(db.system_events.find().sort('timestamp', -1).limit(20))
            return [
                {
                    "title": event.get('event_type', 'System Event'),
                    "time": event.get('timestamp', datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
                            if isinstance(event.get('timestamp'), datetime) else str(event.get('timestamp', '')),
                    "description": event.get('description', 'No description available'),
                    "level": event.get('level', 'Info').title(),
                    "level_badge": "bg-success" if event.get('level') == 'info' else
                                  "bg-warning" if event.get('level') == 'warning' else
                                  "bg-danger" if event.get('level') == 'error' else "bg-info",
                    "type": event.get('event_type', 'System')
                } for event in events
            ]
        else:
            # Generate startup event if no events in database
            return [
                {
                    "title": "Dashboard Startup",
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "description": f"Dashboard initialized with MongoDB connection: {db is not None}",
                    "level": "Info",
                    "level_badge": "bg-success",
                    "type": "Dashboard"
                }
            ]
    except Exception as e:
        logger.error(f"Error fetching system events: {e}")
        # Fallback event on error
        return [
            {
                "title": "Dashboard Error",
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "description": f"Could not retrieve system events: {str(e)}",
                "level": "Error",
                "level_badge": "bg-danger",
                "type": "Dashboard"
            }
        ]

# Get real-time error logs
ERRORS = get_error_logs()

# Get real-time system events
SYSTEM_EVENTS = get_system_events()

@login_manager.user_loader
def load_user(user_id):
    if user_id == '1':  # Sample admin ID
        return User(1, ADMIN_USERNAME, True)
    return None

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You need admin privileges to access this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def ensure_admin_exists():
    # In a real app, you would check if admin exists and create if not
    pass

@app.route('/')
def index():
    """Landing page with MongoDB status"""
    # Show connection status on landing page
    mongo_status = "Connected" if db is not None else "Disconnected"
    collections = []
    if db is not None:
        try:
            collections = db.list_collection_names()
        except Exception as e:
            logger.error(f"Error listing collections: {e}")
    
    return render_template('index.html', 
                          mongo_status=mongo_status,
                          collections=collections)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = 'remember' in request.form
        
        # Basic authentication - in production use database
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            user = User(1, username, True)
            login_user(user, remember=remember)
            flash('Login successful!', 'success')
            
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
            
    # Simplified login form - in production use flask-wtf
    return render_template('login.html', form={'username': '', 'password': '', 'remember': False})

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# Function to get real-time server stats
def get_server_stats():
    stats = {}
    
    # Discord bot stats
    if bot is not None:
        stats["server_count"] = len(bot.guilds)
        # Safely count members
        user_count = 0
        for guild in bot.guilds:
            if guild.member_count is not None:
                user_count += guild.member_count
        stats["user_count"] = user_count
        stats["uptime_percent"] = 99.8  # TODO: Calculate real uptime from metrics
    else:
        stats["server_count"] = 0
        stats["user_count"] = 0
        stats["uptime_percent"] = 0
    
    # Database stats
    if db is not None:
        try:
            # Count commands from feedback collection if available
            if 'feedback' in db.list_collection_names():
                stats["command_count"] = db.feedback.count_documents({})
            else:
                stats["command_count"] = 0
        except Exception as e:
            logger.error(f"Error getting command count: {e}")
            stats["command_count"] = 0
    else:
        stats["command_count"] = 0
    
    # System stats
    try:
        stats["cpu_usage"] = psutil.cpu_percent()
        stats["memory_usage"] = psutil.virtual_memory().percent
        stats["disk_usage"] = psutil.disk_usage('/').percent
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        stats["cpu_usage"] = 0
        stats["memory_usage"] = 0
        stats["disk_usage"] = 0
        
    return stats

@app.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # Get real-time stats
    stats = get_server_stats()
    
    return render_template(
        'dashboard.html',
        server_count=stats["server_count"],
        user_count=stats["user_count"],
        command_count=stats["command_count"],
        uptime_percent=stats["uptime_percent"],
        cpu_usage=stats["cpu_usage"],
        memory_usage=stats["memory_usage"],
        disk_usage=stats["disk_usage"],
        errors=ERRORS[:2]  # Just show the first 2 errors
    )

@app.route('/users')
@login_required
@admin_required
def users():
    # In a real app, fetch user data from MongoDB
    return render_template('users.html')

@app.route('/api/stats')
@login_required
@admin_required
def api_stats():
    """API endpoint for stats - used for AJAX updates"""
    # Get fresh real-time stats
    stats = get_server_stats()
    
    return jsonify({
        "server_count": stats["server_count"],
        "user_count": stats["user_count"],
        "command_count": stats["command_count"],
        "uptime_percent": stats["uptime_percent"],
        "cpu_usage": stats["cpu_usage"],
        "memory_usage": stats["memory_usage"],
        "disk_usage": stats["disk_usage"],
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route('/api/toggle-theme', methods=['POST'])
def toggle_theme():
    """API endpoint to toggle theme preference"""
    data = request.get_json()
    theme = data.get('theme', 'dark')
    session['theme'] = theme
    return jsonify({"status": "success", "theme": theme})

@app.route('/error_logs')
@login_required
@admin_required
def error_logs():
    # Get fresh error logs from the database
    current_errors = get_error_logs()
    
    # Count critical and warning errors safely
    critical_count = 0
    warning_count = 0
    for e in current_errors:
        if e.get('severity') == 'Critical':
            critical_count += 1
        elif e.get('severity') == 'Warning':
            warning_count += 1
    
    return render_template(
        'error_logs.html',
        errors=current_errors,
        error_count=len(current_errors),
        critical_count=critical_count,
        warning_count=warning_count
    )

# Function to get detailed system stats
def get_detailed_system_stats():
    stats = {}
    
    # System resource stats
    try:
        # CPU stats
        stats["cpu_usage"] = psutil.cpu_percent()
        stats["cpu_cores"] = psutil.cpu_count(logical=True)
        
        # Memory stats
        memory = psutil.virtual_memory()
        stats["memory_usage"] = memory.percent
        stats["memory_used"] = f"{memory.used / (1024 * 1024 * 1024):.1f} GB"
        stats["memory_total"] = f"{memory.total / (1024 * 1024 * 1024):.1f} GB"
        
        # Disk stats
        disk = psutil.disk_usage('/')
        stats["disk_usage"] = disk.percent
        stats["disk_used"] = f"{disk.used / (1024 * 1024 * 1024):.1f} GB"
        stats["disk_total"] = f"{disk.total / (1024 * 1024 * 1024):.1f} GB"
        
        # Network stats - simplified, could be enhanced with monitoring
        stats["network_speed"] = "- MB/s"
        stats["network_up"] = "- MB/s"
        stats["network_down"] = "- MB/s"
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        # Set defaults if we can't get actual data
        stats["cpu_usage"] = 0
        stats["cpu_cores"] = 1
        stats["memory_usage"] = 0
        stats["memory_used"] = "0 GB"
        stats["memory_total"] = "0 GB"
        stats["disk_usage"] = 0
        stats["disk_used"] = "0 GB"
        stats["disk_total"] = "0 GB"
        stats["network_speed"] = "- MB/s"
        stats["network_up"] = "- MB/s"
        stats["network_down"] = "- MB/s"
    
    # MongoDB stats
    if db is not None:
        try:
            # Get MongoDB stats
            db_stats = db.command("dbStats")
            stats["mongo_db_size"] = f"{db_stats.get('dataSize', 0) / (1024 * 1024):.1f} MB"
            stats["mongo_collection_count"] = db_stats.get('collections', 0)
            stats["mongo_document_count"] = f"{db_stats.get('objects', 0):,}"
            stats["mongo_connection_type"] = "Direct"
            stats["mongo_host"] = MONGO_URI.split('@')[-1] if MONGO_URI else "Unknown"
            stats["mongo_pool_size"] = 10  # Default value
            
            # These would require custom monitoring in production
            stats["mongo_avg_query_time"] = "-"
            stats["mongo_queries_per_second"] = "-"
        except Exception as e:
            logger.error(f"Error getting MongoDB stats: {e}")
            stats["mongo_db_size"] = "- MB"
            stats["mongo_collection_count"] = 0
            stats["mongo_document_count"] = "-"
            stats["mongo_connection_type"] = "Unknown"
            stats["mongo_host"] = "Unknown"
            stats["mongo_pool_size"] = 0
            stats["mongo_avg_query_time"] = "-"
            stats["mongo_queries_per_second"] = "-"
    else:
        stats["mongo_db_size"] = "- MB"
        stats["mongo_collection_count"] = 0
        stats["mongo_document_count"] = "-"
        stats["mongo_connection_type"] = "Disconnected"
        stats["mongo_host"] = "Unknown"
        stats["mongo_pool_size"] = 0
        stats["mongo_avg_query_time"] = "-"
        stats["mongo_queries_per_second"] = "-"
    
    # Discord API stats (approximations - would need actual monitoring in production)
    if bot is not None:
        # These would ideally come from actual monitoring in production
        stats["discord_messages_calls"] = 0
        stats["discord_messages_response"] = 0
        stats["discord_guilds_calls"] = 0
        stats["discord_guilds_response"] = 0
        stats["discord_members_calls"] = 0
        stats["discord_members_response"] = 0
        stats["discord_channels_calls"] = 0
        stats["discord_channels_response"] = 0
    else:
        stats["discord_messages_calls"] = 0
        stats["discord_messages_response"] = 0
        stats["discord_guilds_calls"] = 0
        stats["discord_guilds_response"] = 0
        stats["discord_members_calls"] = 0
        stats["discord_members_response"] = 0
        stats["discord_channels_calls"] = 0
        stats["discord_channels_response"] = 0
    
    return stats

@app.route('/server_stats')
@login_required
@admin_required
def server_stats():
    # Get real detailed system stats
    stats = get_detailed_system_stats()
    
    # Get fresh system events
    system_events = get_system_events()
    
    return render_template(
        'server_stats.html',
        cpu_usage=stats["cpu_usage"],
        memory_usage=stats["memory_usage"],
        disk_usage=stats["disk_usage"],
        memory_used=stats["memory_used"],
        memory_total=stats["memory_total"],
        disk_used=stats["disk_used"],
        disk_total=stats["disk_total"],
        network_speed=stats["network_speed"],
        network_up=stats["network_up"],
        network_down=stats["network_down"],
        mongo_avg_query_time=stats["mongo_avg_query_time"],
        mongo_queries_per_second=stats["mongo_queries_per_second"],
        mongo_db_size=stats["mongo_db_size"],
        mongo_collection_count=stats["mongo_collection_count"],
        mongo_document_count=stats["mongo_document_count"],
        mongo_connection_type=stats["mongo_connection_type"],
        mongo_host=stats["mongo_host"],
        mongo_pool_size=stats["mongo_pool_size"],
        discord_messages_calls=stats["discord_messages_calls"],
        discord_messages_response=stats["discord_messages_response"],
        discord_guilds_calls=stats["discord_guilds_calls"],
        discord_guilds_response=stats["discord_guilds_response"],
        discord_members_calls=stats["discord_members_calls"],
        discord_members_response=stats["discord_members_response"],
        discord_channels_calls=stats["discord_channels_calls"],
        discord_channels_response=stats["discord_channels_response"],
        cpu_cores=stats["cpu_cores"],
        system_events=system_events
    )

@app.route('/commands')
@login_required
@admin_required
def commands():
    # In a real app, fetch command usage stats from MongoDB
    return render_template('commands.html')

@app.route('/settings')
@login_required
@admin_required
def settings():
    """User settings page"""
    return render_template('settings.html')

@app.context_processor
def inject_theme():
    """Inject theme preference into all templates"""
    return {'theme': session.get('theme', 'dark')}

# Create a basic form class for login (in production, use Flask-WTF)
class LoginForm:
    def __init__(self):
        self.username = {'errors': []}
        self.password = {'errors': []}
        self.remember = {'errors': []}
        
    def hidden_tag(self):
        return ''

# Ensure admin exists on startup
ensure_admin_exists()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7777, debug=True)