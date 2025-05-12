import re
import datetime
import discord

def format_duration(seconds):
    """Format a duration in seconds to a human-readable string"""
    if seconds < 60:
        return f"{seconds} seconds"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes} minute(s), {remaining_seconds} second(s)"
    else:
        hours = seconds // 3600
        remaining_seconds = seconds % 3600
        minutes = remaining_seconds // 60
        seconds = remaining_seconds % 60
        return f"{hours} hour(s), {minutes} minute(s), {seconds} second(s)"

def truncate_text(text, max_length=2000):
    """Truncate text to a maximum length"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def parse_time(time_string):
    """Parse a time string into seconds
    
    Formats:
    - 5s (5 seconds)
    - 2m (2 minutes)
    - 1h (1 hour)
    - 1d (1 day)
    - 1w (1 week)
    """
    time_regex = re.compile(r"(\d+)([smhdw])")
    match = time_regex.match(time_string.lower())
    
    if not match:
        return None
        
    amount, unit = match.groups()
    amount = int(amount)
    
    if unit == 's':
        return amount
    elif unit == 'm':
        return amount * 60
    elif unit == 'h':
        return amount * 3600
    elif unit == 'd':
        return amount * 86400
    elif unit == 'w':
        return amount * 604800
    else:
        return None

def create_embed(title=None, description=None, color=None, author=None, footer=None, thumbnail=None, fields=None):
    """Create a Discord embed with the given parameters"""
    # Default color if none provided
    if color is None:
        color = discord.Color.blue()
        
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    
    # Add author
    if author:
        name = author.get("name", "")
        icon_url = author.get("icon_url", None)
        url = author.get("url", None)
        embed.set_author(name=name, icon_url=icon_url, url=url)
    
    # Add footer
    if footer:
        text = footer.get("text", "")
        icon_url = footer.get("icon_url", None)
        embed.set_footer(text=text, icon_url=icon_url)
    
    # Add thumbnail
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    
    # Add fields
    if fields:
        for field in fields:
            name = field.get("name", "")
            value = field.get("value", "")
            inline = field.get("inline", False)
            embed.add_field(name=name, value=value, inline=inline)
    
    return embed

def get_relative_time(dt):
    """Convert a datetime to a relative time string (e.g., '2 hours ago')"""
    now = datetime.datetime.utcnow()
    
    if isinstance(dt, int):
        dt = datetime.datetime.fromtimestamp(dt)
    
    diff = now - dt
    
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return f"{int(seconds)} seconds ago"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    elif seconds < 2592000:
        weeks = int(seconds / 604800)
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"
    elif seconds < 31536000:
        months = int(seconds / 2592000)
        return f"{months} month{'s' if months != 1 else ''} ago"
    else:
        years = int(seconds / 31536000)
        return f"{years} year{'s' if years != 1 else ''} ago"
