"""
Gunicorn configuration file for Render deployment
"""
import os
import multiprocessing

# Bind to 0.0.0.0:$PORT
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"

# Number of worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = "info"

# Timeouts
timeout = 120
keepalive = 5

# Set for production deployment (optional)
preload_app = True

# Disable automatic restart (Render handles this)
max_requests = 0

# Security - if using behind a proxy like nginx or Render
proxy_protocol = True
forwarded_allow_ips = "*"