"""
Discord Economy Bot Runner
This file orchestrates running both the Discord bot and the web dashboard.
It's set up to work with different deployment environments:
- For Render: Render.yaml will specify the service (bot.py or app.py)
- For GitHub: This file can be used to run both or choose one based on arguments
"""
import os
import sys
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def start_bot():
    """Start the Discord bot component"""
    from bot import run_bot
    print("Starting Discord bot...")
    run_bot()

def start_dashboard():
    """Start the Flask dashboard component"""
    from app import app as flask_app
    import threading
    
    # Start flask in a thread in development
    def run_flask():
        flask_app.run(host='0.0.0.0', port=7777, debug=False)
    
    thread = threading.Thread(target=run_flask)
    thread.daemon = True
    thread.start()
    print("Dashboard running on port 7777")

def main():
    """Main function to decide what to run based on arguments or environment"""
    parser = argparse.ArgumentParser(description='Run Discord Economy Bot components')
    parser.add_argument('--bot', action='store_true', help='Run only the Discord bot')
    parser.add_argument('--dashboard', action='store_true', help='Run only the web dashboard')
    parser.add_argument('--all', action='store_true', help='Run both the bot and dashboard')
    
    args = parser.parse_args()
    
    # Check which components to run
    if args.bot:
        start_bot()
    elif args.dashboard:
        start_dashboard()
        # Keep main thread alive
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            print("Dashboard stopped")
    elif args.all:
        start_dashboard()
        start_bot()  # This will block until the bot exits
    else:
        # Default behavior - good for Render deployment
        if os.environ.get('RENDER_SERVICE_TYPE') == 'worker':
            start_bot()
        else:
            # Import app for Gunicorn in web service
            from app import app
    
if __name__ == "__main__":
    main()

# For Gunicorn to import Flask app
from app import app