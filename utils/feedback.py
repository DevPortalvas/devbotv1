import discord
import os
import time
from discord.ext import commands
from pymongo import MongoClient

# MongoDB connection
mongo_client = MongoClient(os.environ.get("MONGO_URI"))
db = mongo_client['discord_economy']

# Create a collection for feedback if it doesn't exist
if 'feedback' not in db.list_collection_names():
    db.create_collection('feedback')

class FeedbackView(discord.ui.View):
    def __init__(self, command_name, user_id):
        super().__init__(timeout=120)  # Timeout after 2 minutes
        self.command_name = command_name
        self.user_id = user_id
        self.feedback_given = False
    
    async def on_timeout(self):
        # Remove buttons when timeout
        for item in self.children:
            item.disabled = True
        
        # Try to edit the message to remove buttons
        try:
            if hasattr(self, 'message') and self.message:
                await self.message.edit(view=self)
        except Exception as e:
            print(f"Error disabling feedback buttons on timeout: {e}")
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Only allow the original command user to provide feedback
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Only the command user can provide feedback.", ephemeral=True)
            return False
        return True
    
    @discord.ui.button(label="👍", style=discord.ButtonStyle.green, custom_id="feedback_positive")
    async def positive_feedback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._record_feedback(interaction, "positive")
    
    @discord.ui.button(label="👎", style=discord.ButtonStyle.red, custom_id="feedback_negative")
    async def negative_feedback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._record_feedback(interaction, "negative")
    
    async def _record_feedback(self, interaction: discord.Interaction, feedback_type):
        # Don't allow multiple feedback submissions
        if self.feedback_given:
            await interaction.response.send_message("You've already provided feedback.", ephemeral=True)
            return
        
        self.feedback_given = True
        
        # Store feedback in database
        feedback_data = {
            "command": self.command_name,
            "user_id": str(self.user_id),
            "type": feedback_type,
            "timestamp": time.time(),
            "guild_id": str(interaction.guild_id) if interaction.guild else None
        }
        
        try:
            db.feedback.insert_one(feedback_data)
            
            # Disable all buttons
            for item in self.children:
                item.disabled = True
                
            # Update the message to show feedback was received
            await interaction.response.edit_message(view=self)
            
            # Send confirmation
            await interaction.followup.send(f"Thank you for your feedback!", ephemeral=True)
            
            # Save the message reference for timeout handling
            self.message = interaction.message
            
        except Exception as e:
            print(f"Error recording feedback: {e}")
            await interaction.response.send_message("Error recording feedback. Please try again later.", ephemeral=True)

def add_feedback_buttons(command_name, user_id):
    """Creates a view with feedback buttons for a specific command"""
    return FeedbackView(command_name, user_id)

async def get_command_feedback_stats(command_name=None):
    """Get feedback statistics for all commands or a specific command"""
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
    
    if command_name:
        pipeline.insert(0, {"$match": {"command": command_name}})
    
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
    
    return formatted_stats