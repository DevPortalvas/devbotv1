import discord
from discord.ext import commands
import logging
import random
import aiohttp
import asyncio

logger = logging.getLogger("bot")

class Fun(commands.Cog):
    """Fun commands for the bot"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="8ball")
    async def eight_ball(self, ctx, *, question=None):
        """Ask the magic 8-ball a question"""
        if question is None:
            await ctx.send("You need to ask a question!")
            return
            
        responses = [
            "It is certain.",
            "It is decidedly so.",
            "Without a doubt.",
            "Yes, definitely.",
            "You may rely on it.",
            "As I see it, yes.",
            "Most likely.",
            "Outlook good.",
            "Yes.",
            "Signs point to yes.",
            "Reply hazy, try again.",
            "Ask again later.",
            "Better not tell you now.",
            "Cannot predict now.",
            "Concentrate and ask again.",
            "Don't count on it.",
            "My reply is no.",
            "My sources say no.",
            "Outlook not so good.",
            "Very doubtful."
        ]
        
        embed = discord.Embed(
            title="🎱 Magic 8-Ball",
            color=discord.Color.purple()
        )
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=random.choice(responses), inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="roll")
    async def roll(self, ctx, dice: str = "1d6"):
        """Roll dice in NdN format"""
        try:
            number, sides = map(int, dice.split('d'))
            
            if number <= 0 or sides <= 0 or number > 100 or sides > 1000:
                await ctx.send("Invalid dice format. Use NdN where 0 < N ≤ 100 for number of dice and 0 < N ≤ 1000 for sides.")
                return
                
            results = [random.randint(1, sides) for _ in range(number)]
            total = sum(results)
            
            if number == 1:
                await ctx.send(f"🎲 You rolled a {total}!")
            else:
                result_text = ", ".join(str(r) for r in results)
                await ctx.send(f"🎲 You rolled {dice}: {result_text}\nTotal: {total}")
                
        except (ValueError, TypeError):
            await ctx.send("Invalid dice format. Use NdN format (e.g. 1d6, 2d20)")
    
    @commands.command(name="joke")
    async def joke(self, ctx):
        """Get a random joke"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://official-joke-api.appspot.com/random_joke") as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        embed = discord.Embed(
                            title="Random Joke",
                            color=discord.Color.gold()
                        )
                        embed.add_field(name=data["setup"], value=data["punchline"], inline=False)
                        
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send("Sorry, I couldn't fetch a joke right now.")
        except Exception as e:
            logger.error(f"Error fetching joke: {e}", exc_info=True)
            await ctx.send("Sorry, I couldn't fetch a joke right now.")
    
    @commands.command(name="flip")
    async def flip(self, ctx):
        """Flip a coin"""
        result = random.choice(["Heads", "Tails"])
        
        embed = discord.Embed(
            title="Coin Flip",
            description=f"The coin landed on: **{result}**",
            color=discord.Color.gold()
        )
        
        # Use unicode characters for coin faces
        if result == "Heads":
            embed.set_thumbnail(url="https://i.imgur.com/HAvGDuC.png")  # URL to heads image
        else:
            embed.set_thumbnail(url="https://i.imgur.com/XbgzQrd.png")  # URL to tails image
            
        await ctx.send(embed=embed)
    
    @commands.command(name="choose")
    async def choose(self, ctx, *, options):
        """Choose between multiple options"""
        options_list = [option.strip() for option in options.split(',')]
        
        if len(options_list) < 2:
            await ctx.send("Please provide at least two options separated by commas.")
            return
            
        chosen = random.choice(options_list)
        await ctx.send(f"I choose: **{chosen}**")
