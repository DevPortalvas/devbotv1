import discord
from discord.ext import commands
from discord import app_commands
import math

class HelpButtons(discord.ui.View):
    def __init__(self, commands_list, page=0):
        super().__init__(timeout=180)
        self.commands_list = commands_list
        self.page = page
        self.max_pages = math.ceil(len(commands_list) / 5) - 1

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.gray)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
            await interaction.response.edit_message(embed=self.get_page_embed(), view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="Next", style=discord.ButtonStyle.gray)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < self.max_pages:
            self.page += 1
            await interaction.response.edit_message(embed=self.get_page_embed(), view=self)
        else:
            await interaction.response.defer()

    def get_page_embed(self):
        start_idx = self.page * 5
        end_idx = start_idx + 5
        current_page_commands = self.commands_list[start_idx:end_idx]

        embed = discord.Embed(
            title="📚 Command Help Menu",
            description=f"Page {self.page + 1}/{self.max_pages + 1}",
            color=discord.Color.blue()
        )

        for cmd in current_page_commands:
            try:
                # Get command name
                name = cmd.name if hasattr(cmd, 'name') else str(cmd)
                
                # Determine if it's a slash command
                is_slash = isinstance(cmd, app_commands.Command)
                cmd_prefix = "/" if is_slash else "d!"
                
                # Get description, with multiple fallbacks
                description = None
                if hasattr(cmd, 'help') and cmd.help:
                    description = cmd.help
                elif hasattr(cmd, 'description') and cmd.description:
                    description = cmd.description
                elif hasattr(cmd, 'callback') and cmd.callback.__doc__:
                    description = cmd.callback.__doc__
                
                if not description:
                    description = "No description provided"
                
                # Get aliases if available
                aliases_text = ""
                if hasattr(cmd, 'aliases') and cmd.aliases:
                    aliases = ", ".join([f"{alias}" for alias in cmd.aliases])
                    aliases_text = f"\n**Aliases:** {aliases}"
                
                # Format the field value
                cmd_type = "Slash Command" if is_slash else "Text Command"
                value = f"**Type:** {cmd_type}\n**Description:** {description}{aliases_text}"
                
                embed.add_field(name=f"{cmd_prefix}{name}", value=value, inline=False)
                
            except Exception as e:
                print(f"Error processing command {cmd}: {e}")
                continue

        embed.set_footer(text="Use the buttons below to navigate through pages • Use !help or /help to see this menu")
        return embed

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help", help="Shows all available commands")
    async def help_cmd(self, ctx):
        await self._show_help(ctx)

    @app_commands.command(name="help", description="Shows all available commands")
    async def help_slash(self, interaction: discord.Interaction):
        await self._show_help(interaction)

    async def _show_help(self, ctx_or_interaction):
        try:
            # Tester command names to exclude from regular help
            tester_command_names = [
                "thelp", "addtester", "removetester", "listtesters", 
                "testmoney", "resetmoney", "getitem", "inventoryreset"
            ]
            
            # Get all visible commands and app commands, excluding tester commands
            commands_list = [cmd for cmd in self.bot.commands 
                           if not cmd.hidden and cmd.name not in tester_command_names]
            
            # Include slash commands, but exclude tester commands
            for cmd in self.bot.tree.get_commands():
                # Add app commands that aren't tester commands and aren't already represented
                if (cmd.name not in tester_command_names and 
                    not any(regular_cmd.name == cmd.name for regular_cmd in commands_list)):
                    commands_list.append(cmd)
            
            # Create view with buttons
            view = HelpButtons(commands_list)
            embed = view.get_page_embed()

            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(embed=embed, view=view)
            else:
                await ctx_or_interaction.send(embed=embed, view=view)
        except Exception as e:
            print(f"Error in help command: {e}")
            error_embed = discord.Embed(
                title="Error",
                description="An error occurred while showing the help menu. Please try again later.",
                color=discord.Color.red()
            )
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(embed=error_embed, ephemeral=True)
            else:
                await ctx_or_interaction.send(embed=error_embed)

async def setup(bot):
    await bot.add_cog(Help(bot))
    
