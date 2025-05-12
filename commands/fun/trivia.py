import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import html
import random
import asyncio

class Trivia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.categories = {
            "general": 9,
            "books": 10,
            "film": 11,
            "music": 12,
            "television": 14,
            "videogames": 15,
            "science": 17,
            "computers": 18,
            "mathematics": 19,
            "sports": 21,
            "geography": 22,
            "history": 23,
            "politics": 24,
            "art": 25,
            "animals": 27,
            "vehicles": 28,
            "comics": 29,
            "anime": 31,
            "cartoons": 32
        }
        self.difficulty_colors = {
            "easy": 0x2ECC71,  # Green
            "medium": 0xF1C40F,  # Gold
            "hard": 0xE74C3C    # Red
        }
        
    @commands.command(name="trivia", help="Start a trivia game. Optional: specify category and difficulty (easy/medium/hard)")
    async def trivia(self, ctx, category: str = None, difficulty: str = None):
        await self._start_trivia(ctx, category, difficulty)
        
    @app_commands.command(name="trivia", description="Start a trivia game")
    @app_commands.describe(
        category="The category of trivia questions",
        difficulty="The difficulty level (easy, medium, hard)"
    )
    @app_commands.choices(
        difficulty=[
            app_commands.Choice(name="Easy", value="easy"),
            app_commands.Choice(name="Medium", value="medium"),
            app_commands.Choice(name="Hard", value="hard")
        ]
    )
    async def trivia_slash(self, interaction: discord.Interaction, category: str = None, difficulty: str = None):
        await self._start_trivia(interaction, category, difficulty)
        
    async def _start_trivia(self, ctx_or_interaction, category=None, difficulty=None):
        # Validate category
        category_id = None
        if category:
            category = category.lower()
            if category in self.categories:
                category_id = self.categories[category]
            else:
                categories_list = ", ".join(f"`{c}`" for c in self.categories.keys())
                embed = discord.Embed(
                    title="Invalid Category",
                    description=f"Available categories: {categories_list}",
                    color=0xE74C3C  # Red
                )
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await ctx_or_interaction.send(embed=embed)
                return
                
        # Validate difficulty
        if difficulty and difficulty.lower() not in ["easy", "medium", "hard"]:
            embed = discord.Embed(
                title="Invalid Difficulty",
                description="Difficulty must be one of: `easy`, `medium`, `hard`",
                color=0xE74C3C  # Red
            )
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await ctx_or_interaction.send(embed=embed)
            return
            
        # Build API URL
        api_url = "https://opentdb.com/api.php?amount=1&encode=url3986&type=multiple"
        if category_id:
            api_url += f"&category={category_id}"
        if difficulty:
            api_url += f"&difficulty={difficulty.lower()}"
            
        try:
            # Fetch trivia question
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as response:
                    if response.status != 200:
                        raise Exception(f"API returned status code {response.status}")
                    
                    data = await response.json()
                    if data["response_code"] != 0 or not data["results"]:
                        raise Exception("Failed to get trivia question")
                    
                    question_data = data["results"][0]
                    
            # Process the question data
            question = html.unescape(question_data["question"])
            correct_answer = html.unescape(question_data["correct_answer"])
            incorrect_answers = [html.unescape(a) for a in question_data["incorrect_answers"]]
            
            # Create answer choices
            all_answers = incorrect_answers + [correct_answer]
            random.shuffle(all_answers)
            
            # Create embed
            category_name = html.unescape(question_data["category"])
            question_difficulty = question_data["difficulty"]
            
            embed = discord.Embed(
                title=f"Trivia: {category_name}",
                description=f"**{question}**",
                color=self.difficulty_colors.get(question_difficulty, 0x3498DB)  # Default blue
            )
            
            # Add answer choices with letters
            answer_text = ""
            letters = ["A", "B", "C", "D"]
            correct_letter = None
            
            for i, answer in enumerate(all_answers):
                letter = letters[i]
                answer_text += f"{letter}. {answer}\n"
                if answer == correct_answer:
                    correct_letter = letter
                    
            embed.add_field(name="Answers", value=answer_text, inline=False)
            embed.set_footer(text=f"Difficulty: {question_difficulty.capitalize()} | You have 15 seconds to answer")
            
            # Create answer buttons
            class AnswerButton(discord.ui.Button):
                def __init__(self, letter, style=discord.ButtonStyle.primary):
                    super().__init__(label=letter, style=style)
                    self.letter = letter
                    
                async def callback(self, interaction: discord.Interaction):
                    # Original user check
                    original_user = ctx_or_interaction.author if hasattr(ctx_or_interaction, 'author') else ctx_or_interaction.user
                    if interaction.user.id != original_user.id:
                        await interaction.response.send_message("This isn't your trivia question!", ephemeral=True)
                        return
                        
                    # Check answer
                    is_correct = self.letter == correct_letter
                    
                    # Create result embed
                    if is_correct:
                        result_embed = discord.Embed(
                            title="Correct!",
                            description=f"**{question}**\n\nThe answer was: **{correct_answer}**",
                            color=0x2ECC71  # Green
                        )
                    else:
                        result_embed = discord.Embed(
                            title="Wrong!",
                            description=f"**{question}**\n\nThe correct answer was: **{correct_answer}**",
                            color=0xE74C3C  # Red
                        )
                        
                    # Edit the message to show result
                    self.view.stop()
                    await interaction.response.edit_message(embed=result_embed, view=None)
            
            # Create view with answer buttons
            view = discord.ui.View(timeout=15.0)
            for letter in letters:
                view.add_item(AnswerButton(letter))
                
            # Add timeout handler
            async def on_timeout():
                timeout_embed = discord.Embed(
                    title="Time's Up!",
                    description=f"**{question}**\n\nThe correct answer was: **{correct_answer}**",
                    color=0x7F8C8D  # Gray
                )
                
                # Get the message
                message = None
                if isinstance(ctx_or_interaction, discord.Interaction):
                    if hasattr(ctx_or_interaction, "original_response"):
                        try:
                            message = await ctx_or_interaction.original_response()
                        except:
                            pass
                else:
                    message = await ctx_or_interaction.channel.fetch_message(ctx_or_interaction.message.id)
                    
                if message:
                    await message.edit(embed=timeout_embed, view=None)
            
            view.on_timeout = on_timeout
            
            # Send the question
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(embed=embed, view=view)
            else:
                await ctx_or_interaction.send(embed=embed, view=view)
                
        except Exception as e:
            print(f"Error in trivia command: {e}")
            error_embed = discord.Embed(
                title="Error",
                description="Failed to fetch a trivia question. Please try again later.",
                color=0xE74C3C  # Red
            )
            if isinstance(ctx_or_interaction, discord.Interaction):
                if not ctx_or_interaction.response.is_done():
                    await ctx_or_interaction.response.send_message(embed=error_embed, ephemeral=True)
                else:
                    await ctx_or_interaction.followup.send(embed=error_embed, ephemeral=True)
            else:
                await ctx_or_interaction.send(embed=error_embed)

async def setup(bot):
    await bot.add_cog(Trivia(bot))