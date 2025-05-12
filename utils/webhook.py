import discord
import asyncio
import datetime
import aiohttp
import json
import socket
import psutil
import platform
import os
from utils.database import DatabaseConnection

class WebhookManager:
    """Class to manage Discord webhook for bot status reporting"""
    
    def __init__(self, webhook_url, bot, db_connection):
        self.webhook_url = webhook_url
        self.bot = bot
        self.db = db_connection
        self.hostname = socket.gethostname()
        self.online = False
        self.startup_time = datetime.datetime.utcnow()
        
    async def initialize(self):
        """Send initial startup message"""
        self.online = True
        await self.send_webhook({
            "embeds": [{
                "title": "Bot Online",
                "description": f"**{self.bot.user.name}** is now online on **{self.hostname}**",
                "color": 0x2ECC71,  # Green
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "fields": [
                    {
                        "name": "Bot User",
                        "value": f"{self.bot.user.name} ({self.bot.user.id})",
                        "inline": True
                    },
                    {
                        "name": "Server Count",
                        "value": str(len(self.bot.guilds)),
                        "inline": True
                    },
                    {
                        "name": "Python Version",
                        "value": platform.python_version(),
                        "inline": True
                    }
                ],
                "footer": {
                    "text": f"Bot Instance ID: {self.hostname}"
                }
            }]
        })
    
    async def update_status(self):
        """Task to update bot status periodically"""
        await asyncio.sleep(60)  # Wait 1 minute after startup before first update
        
        while self.online:
            try:
                # Get system stats
                cpu_percent = psutil.cpu_percent()
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                uptime = (datetime.datetime.utcnow() - self.startup_time).total_seconds()
                
                # Format uptime
                days, remainder = divmod(uptime, 86400)
                hours, remainder = divmod(remainder, 3600)
                minutes, seconds = divmod(remainder, 60)
                uptime_str = f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"
                
                # Get database stats
                try:
                    user_count = self.db.economies.estimated_document_count()
                except:
                    user_count = "Unknown"
                
                # Send status update
                await self.send_webhook({
                    "embeds": [{
                        "title": "Bot Status Update",
                        "color": 0x3498DB,  # Blue
                        "timestamp": datetime.datetime.utcnow().isoformat(),
                        "fields": [
                            {
                                "name": "Uptime",
                                "value": uptime_str,
                                "inline": True
                            },
                            {
                                "name": "Server Count",
                                "value": str(len(self.bot.guilds)),
                                "inline": True
                            },
                            {
                                "name": "User Count",
                                "value": str(sum(guild.member_count for guild in self.bot.guilds)),
                                "inline": True
                            },
                            {
                                "name": "CPU Usage",
                                "value": f"{cpu_percent}%",
                                "inline": True
                            },
                            {
                                "name": "Memory Usage",
                                "value": f"{memory.percent}%",
                                "inline": True
                            },
                            {
                                "name": "Disk Usage",
                                "value": f"{disk.percent}%",
                                "inline": True
                            },
                            {
                                "name": "Database Users",
                                "value": str(user_count),
                                "inline": True
                            }
                        ],
                        "footer": {
                            "text": f"Bot Instance ID: {self.hostname}"
                        }
                    }]
                })
                
            except Exception as e:
                print(f"Error in status update: {e}")
                
            # Wait 30 minutes before next update
            await asyncio.sleep(1800)
    
    async def set_offline(self):
        """Mark the bot as offline"""
        self.online = False
        
        try:
            await self.send_webhook({
                "embeds": [{
                    "title": "Bot Offline",
                    "description": f"**{self.bot.user.name}** is shutting down on **{self.hostname}**",
                    "color": 0xE74C3C,  # Red
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    "fields": [
                        {
                            "name": "Uptime",
                            "value": str(datetime.datetime.utcnow() - self.startup_time),
                            "inline": True
                        }
                    ],
                    "footer": {
                        "text": f"Bot Instance ID: {self.hostname}"
                    }
                }]
            })
        except Exception as e:
            print(f"Error sending offline status: {e}")
    
    async def send_webhook(self, data):
        """Send data to webhook"""
        try:
            async with self.bot.session.post(
                self.webhook_url,
                json=data,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status != 204:
                    print(f"Failed to send webhook: {response.status}")
        except Exception as e:
            print(f"Error sending webhook: {e}")