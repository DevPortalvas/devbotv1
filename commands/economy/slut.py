import discord
from discord.ext import commands
from discord import app_commands
import random
from utils.database import update_balance  
from utils.feedback import add_feedback_buttons
  
class Slut(commands.Cog):  
    def __init__(self, bot):  
        self.bot = bot  
  
    @commands.command(name="slut", help="Do dirty stuff for money;)", aliases=['dirty', 'lewd'])  
    @commands.cooldown(1, 600, commands.BucketType.member)  
    async def slut(self, ctx):  
        await self._do_slut(ctx)  
  
    @app_commands.command(name="slut", description="Do dirty stuff for money;)")  
    @app_commands.checks.cooldown(1, 600, key=lambda i: (i.guild_id, i.user.id))  
    async def slut_slash(self, interaction: discord.Interaction):  
        await self._do_slut(interaction)  
  
    async def _do_slut(self, ctx_or_interaction):  
        user_id = ctx_or_interaction.user.id if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author.id  
        earnings = random.randint(3000, 6000)  
  
        messages = [  
            f"You sucked someone off, you made ${earnings}!",  
            f"your ass is cooked now but at least you made ${earnings}!",  
            f"sold feet picks for ${earnings}!",  
            f"You danced in a strip club and made from the tips ${earnings}!",  
            f"You made an only fans and you got ${earnings} somehow",  
            f"You acted as someones dog and made ${earnings}!",  
            f"You followed this desperate mom into the hotel she suggested and made ${earnings}!",  
            f"You had your fun with her, and managed to steal from them ${earnings} tsktsktsk!",  
            f"now you are all white stuff and you made ${earnings}, was it really worth it...? probably yes",  
            f"Had to call dudes 'good boy' now you made ${earnings}! desperate motherfuckers"  
        ]  
  
        result_message = random.choice(messages)  
        guild_id = ctx_or_interaction.guild.id
        update_balance(guild_id, user_id, earnings)  
  
        embed = discord.Embed(title="U MADE SOME MONEY DIRTY SLUTTTTT",   
                            description=result_message,  
                            color=discord.Color.orange()  
                            )  
          
        # Add feedback buttons
        user = ctx_or_interaction.user if hasattr(ctx_or_interaction, 'user') else ctx_or_interaction.author
        feedback_view = add_feedback_buttons("slut", user.id)
            
        if isinstance(ctx_or_interaction, discord.Interaction):  
            await ctx_or_interaction.response.send_message(embed=embed, view=feedback_view)  
        else:  
            message = await ctx_or_interaction.send(embed=embed, view=feedback_view)
            feedback_view.message = message
  
    @slut.error  
    async def slut_error(self, ctx, error):  
        if isinstance(error, commands.CommandOnCooldown):  
            embed = discord.Embed(title="You're tired!",  
                                description=f"come back in {int(error.retry_after // 60)} minutes.",  
                                color=discord.Color.red()  
                                )  
            await ctx.send(embed=embed)  
  
    @slut_slash.error  
    async def work_slash_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):  
        if isinstance(error, app_commands.CommandOnCooldown):  
            embed = discord.Embed(title="hoe chill out you are tired and emotionally traumatised!",  
                                description=f"come back in {int(error.retry_after // 60)} minutes.",  
                                color=discord.Color.red()  
                                )  
            await interaction.response.send_message(embed=embed, ephemeral=True)  
  
async def setup(bot):  
    await bot.add_cog(Slut(bot))