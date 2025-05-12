from flask import Flask
from threading import Thread
from app import app as dashboard_app

# Use our dashboard app instead of creating a new one
app = dashboard_app

def run():
    app.run(host='0.0.0.0', port=7777)  # Changed port to avoid conflicts

def keep_alive():
    t = Thread(target=run)
    t.start()
