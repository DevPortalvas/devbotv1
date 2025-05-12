import os
import time
import json
import datetime
from functools import wraps
from pymongo import MongoClient
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from dotenv import load_dotenv
import psutil
from werkzeug.security import generate_password_hash, check_password_hash

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "supersecretkey")

# Configure login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Connect to MongoDB
MONGO_URI = os.environ.get("MONGO_URI")
mongo_client = MongoClient(MONGO_URI)
db = mongo_client['discord_economy']

# Ensure admin user exists
OWNER_ID = "545609811354583040"  # Your Discord ID

# Define basic User class
class User(UserMixin):
    def __init__(self, user_data):
        self.id = user_data["_id"]
        self.username = user_data.get("username", "Admin")
        self.is_admin = user_data.get("is_admin", False)

@login_manager.user_loader
def load_user(user_id):
    user_data = db.dashboard_users.find_one({"_id": user_id})
    if user_data:
        return User(user_data)
    return None

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("You need admin rights to access this page.")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Ensure admin user exists
def ensure_admin_exists():
    admin = db.dashboard_users.find_one({"_id": OWNER_ID})
    if not admin:
        db.dashboard_users.insert_one({
            "_id": OWNER_ID,
            "username": "Admin",
            "password": generate_password_hash("admin"),  # Default password
            "is_admin": True
        })
        print("Admin user created with default password. Please change it immediately.")

# Call the function to ensure admin exists
ensure_admin_exists()

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        password = request.form.get('password')
        
        user_data = db.dashboard_users.find_one({"_id": user_id})
        if user_data and check_password_hash(user_data.get("password"), password):
            login_user(User(user_data))
            flash('Login successful!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Login failed. Check your credentials.', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get stats for dashboard
    server_count = db.prefixes.count_documents({})
    user_count = db.economies.count_documents({})
    
    # Get top 5 servers by member count
    top_servers = list(db.prefixes.find().sort("member_count", -1).limit(5))
    
    # Get total commands ran in the last 24 hours
    yesterday = time.time() - 86400
    commands_24h = db.command_logs.count_documents({"timestamp": {"$gt": yesterday}})
    
    # Get top 5 commands
    top_commands = list(db.command_logs.aggregate([
        {"$group": {"_id": "$command", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]))
    
    # Get system stats
    cpu_percent = psutil.cpu_percent()
    memory = psutil.virtual_memory()
    memory_percent = memory.percent
    
    # Get feedback stats
    feedback_stats = {}
    feedback_results = list(db.feedback.aggregate([
        {"$group": {
            "_id": {"command": "$command", "type": "$type"},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id.command": 1}}
    ]))
    
    for result in feedback_results:
        command = result["_id"]["command"]
        feedback_type = result["_id"]["type"]
        count = result["count"]
        
        if command not in feedback_stats:
            feedback_stats[command] = {"positive": 0, "negative": 0}
        
        feedback_stats[command][feedback_type] = count
    
    return render_template('dashboard.html', 
                           server_count=server_count,
                           user_count=user_count,
                           top_servers=top_servers,
                           commands_24h=commands_24h,
                           top_commands=top_commands,
                           cpu_percent=cpu_percent,
                           memory_percent=memory_percent,
                           feedback_stats=feedback_stats)

@app.route('/users')
@login_required
@admin_required
def users():
    # Get paginated list of users
    page = int(request.args.get('page', 1))
    per_page = 20
    skip = (page - 1) * per_page
    
    users = list(db.economies.find().skip(skip).limit(per_page))
    total_users = db.economies.count_documents({})
    total_pages = (total_users // per_page) + (1 if total_users % per_page > 0 else 0)
    
    return render_template('users.html', 
                           users=users, 
                           page=page, 
                           total_pages=total_pages)

@app.route('/api/stats')
@login_required
def api_stats():
    """API endpoint for stats - used for AJAX updates"""
    cpu_percent = psutil.cpu_percent()
    memory = psutil.virtual_memory()
    memory_percent = memory.percent
    
    # Get commands in last hour
    hour_ago = time.time() - 3600
    commands_1h = db.command_logs.count_documents({"timestamp": {"$gt": hour_ago}})
    
    # Get users joined in last day
    day_ago = time.time() - 86400
    new_users = db.economies.count_documents({"joined_at": {"$gt": day_ago}})
    
    return jsonify({
        'cpu_percent': cpu_percent,
        'memory_percent': memory_percent,
        'commands_1h': commands_1h,
        'new_users': new_users
    })

@app.route('/api/toggle-theme', methods=['POST'])
def toggle_theme():
    """API endpoint to toggle theme preference"""
    theme = request.json.get('theme', 'dark')
    session['theme'] = theme
    return jsonify({'success': True, 'theme': theme})

@app.route('/feedback')
@login_required
@admin_required
def feedback():
    """View feedback stats"""
    # Get all feedback stats
    pipeline = [
        {"$group": {
            "_id": {
                "command": "$command",
                "type": "$type"
            },
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id.command": 1}}
    ]
    
    results = list(db.feedback.aggregate(pipeline))
    
    # Format the results
    formatted_stats = {}
    for result in results:
        command = result["_id"]["command"]
        feedback_type = result["_id"]["type"]
        count = result["count"]
        
        if command not in formatted_stats:
            formatted_stats[command] = {"positive": 0, "negative": 0}
        
        formatted_stats[command][feedback_type] = count
    
    return render_template('feedback.html', feedback_stats=formatted_stats)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """User settings page"""
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Verify current password
        user_data = db.dashboard_users.find_one({"_id": current_user.id})
        if not check_password_hash(user_data.get("password"), current_password):
            flash('Current password is incorrect.', 'danger')
            return redirect(url_for('settings'))
        
        # Verify new passwords match
        if new_password != confirm_password:
            flash('New passwords do not match.', 'danger')
            return redirect(url_for('settings'))
        
        # Update password
        db.dashboard_users.update_one(
            {"_id": current_user.id},
            {"$set": {"password": generate_password_hash(new_password)}}
        )
        
        flash('Password updated successfully.', 'success')
        return redirect(url_for('settings'))
        
    return render_template('settings.html')

@app.context_processor
def inject_theme():
    """Inject theme preference into all templates"""
    return {'theme': session.get('theme', 'dark')}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)