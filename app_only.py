"""
Standalone version of the Discord Bot Dashboard (without bot)
For use on Render.com
"""
import os
from app import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)