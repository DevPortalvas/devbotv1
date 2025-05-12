
import discord
from discord.ext import commands
from discord import app_commands
import random
from utils.database import get_balance, update_balance
from utils.feedback import add_feedback_buttons

class Steal(commands.Cog):  
    def __init__(self, bot):  
        self.bot = bot  

    @commands.command(help="Attempt to steal money from another user.", aliases=['rob', 'thief'])  
    @commands.cooldown(1, 1800, commands.BucketType.member)  # 30 minutes  
    async def steal(self, ctx, target: discord.Member):  
        await self._do_steal(ctx, ctx.author, target)  

    @app_commands.command(name="steal", description="Attempt to steal money from another user.")  
    @app_commands.checks.cooldown(1, 1800, key=lambda i: (i.guild_id, i.user.id))  
    async def steal_slash(self, interaction: discord.Interaction, target: discord.Member):  
        await self._do_steal(interaction, interaction.user, target)  

    async def _do_steal(self, ctx_or_interaction, thief, target):  
        try:
            guild_id = ctx_or_interaction.guild.id
            if thief.id == target.id:
                embed = discord.Embed(  
                    title="Shrug...",  
                    description="You can't steal from yourself. ¯\\_(ツ)_/¯",  
                    color=discord.Color.light_grey()  
                )  
                return await self._send(ctx_or_interaction, embed, True)  

            thief_bal = get_balance(guild_id, thief.id)
            target_bal = get_balance(guild_id, target.id)  

            if target_bal["pocket"] <= 0:  
                embed = discord.Embed(  
                    title="Oops!",  
                    description=f"{target.display_name} has no pocket money to steal. {random.choice(['No luck!', 'Try someone richer.', 'They broke.'])}",  
                    color=discord.Color.red()  
                )  
                return await self._send(ctx_or_interaction, embed, True)  

            if random.random() < 0.2:  # 20% chance to get caught  
                fine = random.randint(100, 10000)
                thief_bal = get_balance(guild_id, thief.id)
                update_balance(guild_id, thief.id, -fine)
                new_balance = thief_bal["pocket"] - fine
                in_debt = new_balance < 0
                
                embed = discord.Embed(
                    title="Caught! **You got arrested!**",
                    description=f"**{thief.display_name}** was caught trying to steal and has to pay a **${fine:,}** fine!\n\n" + 
                              (f"They are now **${abs(new_balance):,} in debt**! To get out of debt, earn money through work or withdraw from your bank." if in_debt else f"They paid the fine and now have **${new_balance:,}** left."),
                    color=discord.Color.red()
                )
                embed.set_footer(text="Police sirens intensify")  
                return await self._send(ctx_or_interaction, embed)  

            steal_percent = random.uniform(0.03, 1.0)  
            amount_stolen = max(1, int(target_bal["pocket"] * steal_percent))  
            update_balance(guild_id, thief.id, amount_stolen)
            update_balance(guild_id, target.id, -amount_stolen)  

            embed = discord.Embed(  
                title="Success! **You stole some cash!**",  
                description=f"**{thief.display_name}** stole **${amount_stolen}** from **{target.display_name}**! \n\n{random.choice(['Smooth criminal.', 'No witnesses.', 'That was slick.'])}",  
                color=discord.Color.green()  
            )  
            embed.set_footer(text="Don't get too greedy now...")  
            return await self._send(ctx_or_interaction, embed)
        except Exception as e:
            print(f"Error in steal command: {e}")
            error_embed = discord.Embed(
                title="Error",
                description="An error occurred while processing your request.",
                color=discord.Color.red()
            )
            return await self._send(ctx_or_interaction, error_embed, True)

    async def _send(self, ctx_or_interaction, embed, ephemeral=False):  
        # Add feedback buttons
        user = ctx_or_interaction.user if hasattr(ctx_or_interaction, 'user') else ctx_or_interaction.author
        feedback_view = add_feedback_buttons("steal", user.id)
        
        if isinstance(ctx_or_interaction, discord.Interaction):  
            await ctx_or_interaction.response.send_message(embed=embed, view=feedback_view, ephemeral=ephemeral)  
        else:  
            message = await ctx_or_interaction.send(embed=embed, view=feedback_view)
            feedback_view.message = message

    @steal.error  
    async def steal_error(self, ctx, error):  
        if isinstance(error, commands.CommandOnCooldown):  
            minutes = int(error.retry_after // 60)  
            embed = discord.Embed(  
                title="Cooldown!",  
                description=f"You must wait {minutes} minutes before stealing again!",  
                color=discord.Color.orange()  
            )  
            await ctx.send(embed=embed)  

    @steal_slash.error  
    async def steal_slash_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):  
        if isinstance(error, app_commands.CommandOnCooldown):  
            minutes = int(error.retry_after // 60)  
            embed = discord.Embed(  
                title="Cooldown!",  
                description=f"You must wait {minutes} minutes before stealing again!",  
                color=discord.Color.orange()  
            )  
            await interaction.response.send_message(embed=embed, ephemeral=True)  

async def setup(bot):  
    await bot.add_cog(Steal(bot))
