import os
import logging
import json
from datetime import datetime, timedelta
from functools import wraps

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

# Sample admin user - in production, use a proper database
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "password")
OWNER_ID = "545609811354583040"  # Discord ID of the owner

# Mock data for demonstration - these would come from MongoDB in production
MOCK_DATA = {
    "server_count": 25,
    "user_count": 1250,
    "command_count": 3456,
    "uptime_percent": 99.8,
    "cpu_usage": 32,
    "memory_usage": 45,
    "disk_usage": 28,
    "mongo_avg_query_time": 12.5,
    "mongo_queries_per_second": 8.3,
    "mongo_db_size": "1.2 GB",
    "mongo_collection_count": 7,
    "mongo_document_count": "8,520",
    "mongo_connection_type": "Direct",
    "mongo_host": "MongoDB Atlas",
    "mongo_pool_size": 50,
    "network_speed": "3.2 MB/s",
    "network_up": "1.1 MB/s",
    "network_down": "2.1 MB/s",
    "memory_used": "1.5 GB",
    "memory_total": "3.3 GB",
    "disk_used": "5.6 GB",
    "disk_total": "20 GB",
    "discord_messages_calls": 3240,
    "discord_messages_response": 125,
    "discord_guilds_calls": 856,
    "discord_guilds_response": 145,
    "discord_members_calls": 1240,
    "discord_members_response": 178,
    "discord_channels_calls": 945,
    "discord_channels_response": 356,
    "cpu_cores": 2
}

# Sample user for admin access
class User(UserMixin):
    def __init__(self, id, username, is_admin=False):
        self.id = id
        self.username = username
        self.is_admin = is_admin

# Sample errors for error logs page
ERRORS = [
    {
        "id": "ERR-001",
        "timestamp": "2025-05-12 14:32:45",
        "type": "Database",
        "type_badge": "bg-danger",
        "severity": "Critical",
        "severity_badge": "bg-danger",
        "message": "Failed to connect to MongoDB: Connection timed out",
        "location": "utils/database.py:128 in connect()"
    },
    {
        "id": "ERR-002",
        "timestamp": "2025-05-12 15:45:23",
        "type": "API",
        "type_badge": "bg-warning",
        "severity": "Warning",
        "severity_badge": "bg-warning",
        "message": "Discord API rate limit reached for endpoint /guilds/{guild_id}/members",
        "location": "commands/help.py:42 in help_slash()"
    },
    {
        "id": "ERR-003",
        "timestamp": "2025-05-12 16:12:08",
        "type": "Command",
        "type_badge": "bg-info",
        "severity": "Error",
        "severity_badge": "bg-danger",
        "message": "Invalid command syntax: Missing required parameter 'amount'",
        "location": "commands/economy/deposit.py:55 in deposit()"
    }
]

# Sample system events for server stats page
SYSTEM_EVENTS = [
    {
        "title": "System Startup",
        "time": "2025-05-12 08:45:32",
        "description": "Bot started successfully with 24 commands loaded",
        "level": "Info",
        "level_badge": "bg-success",
        "type": "Startup"
    },
    {
        "title": "Database Connection",
        "time": "2025-05-12 08:45:35",
        "description": "Successfully connected to MongoDB Atlas",
        "level": "Info",
        "level_badge": "bg-success",
        "type": "Database"
    },
    {
        "title": "API Rate Limit",
        "time": "2025-05-12 12:32:15",
        "description": "Discord API rate limit reached at 50%, backing off",
        "level": "Warning",
        "level_badge": "bg-warning",
        "type": "API"
    }
]

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
    # Simple landing page
    return render_template('index.html')

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

@app.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # In a real app, fetch this data from MongoDB
    return render_template(
        'dashboard.html',
        server_count=MOCK_DATA['server_count'],
        user_count=MOCK_DATA['user_count'],
        command_count=MOCK_DATA['command_count'],
        uptime_percent=MOCK_DATA['uptime_percent'],
        cpu_usage=MOCK_DATA['cpu_usage'],
        memory_usage=MOCK_DATA['memory_usage'],
        disk_usage=MOCK_DATA['disk_usage'],
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
    # In a real app, fetch fresh data from MongoDB
    return jsonify({
        "server_count": MOCK_DATA['server_count'],
        "user_count": MOCK_DATA['user_count'],
        "command_count": MOCK_DATA['command_count'],
        "uptime_percent": MOCK_DATA['uptime_percent'],
        "cpu_usage": MOCK_DATA['cpu_usage'],
        "memory_usage": MOCK_DATA['memory_usage'],
        "disk_usage": MOCK_DATA['disk_usage'],
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
    # In a real app, fetch error logs from MongoDB
    return render_template(
        'error_logs.html',
        errors=ERRORS,
        error_count=len(ERRORS),
        critical_count=sum(1 for e in ERRORS if e['severity'] == 'Critical'),
        warning_count=sum(1 for e in ERRORS if e['severity'] == 'Warning')
    )

@app.route('/server_stats')
@login_required
@admin_required
def server_stats():
    # In a real app, fetch server stats from MongoDB
    return render_template(
        'server_stats.html',
        cpu_usage=MOCK_DATA['cpu_usage'],
        memory_usage=MOCK_DATA['memory_usage'],
        disk_usage=MOCK_DATA['disk_usage'],
        memory_used=MOCK_DATA['memory_used'],
        memory_total=MOCK_DATA['memory_total'],
        disk_used=MOCK_DATA['disk_used'],
        disk_total=MOCK_DATA['disk_total'],
        network_speed=MOCK_DATA['network_speed'],
        network_up=MOCK_DATA['network_up'],
        network_down=MOCK_DATA['network_down'],
        mongo_avg_query_time=MOCK_DATA['mongo_avg_query_time'],
        mongo_queries_per_second=MOCK_DATA['mongo_queries_per_second'],
        mongo_db_size=MOCK_DATA['mongo_db_size'],
        mongo_collection_count=MOCK_DATA['mongo_collection_count'],
        mongo_document_count=MOCK_DATA['mongo_document_count'],
        mongo_connection_type=MOCK_DATA['mongo_connection_type'],
        mongo_host=MOCK_DATA['mongo_host'],
        mongo_pool_size=MOCK_DATA['mongo_pool_size'],
        discord_messages_calls=MOCK_DATA['discord_messages_calls'],
        discord_messages_response=MOCK_DATA['discord_messages_response'],
        discord_guilds_calls=MOCK_DATA['discord_guilds_calls'],
        discord_guilds_response=MOCK_DATA['discord_guilds_response'],
        discord_members_calls=MOCK_DATA['discord_members_calls'],
        discord_members_response=MOCK_DATA['discord_members_response'],
        discord_channels_calls=MOCK_DATA['discord_channels_calls'],
        discord_channels_response=MOCK_DATA['discord_channels_response'],
        cpu_cores=MOCK_DATA['cpu_cores'],
        system_events=SYSTEM_EVENTS
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