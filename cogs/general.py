import discord
from discord.ext import commands
from discord import app_commands

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="hello", description="Say hello to the bot!")
    async def hello(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Hello, {interaction.user.mention}! I'm ready for the MMORPG. 🎮")

    @app_commands.command(name="commands_list", description="Available commands")
    async def commands_list(self, interaction: discord.Interaction):
        commands_available = [cmd.name for cmd in self.bot.tree.get_commands()]
        await interaction.response.send_message(f"Available commands: {', '.join(commands_available)}")

    @app_commands.command(name="ping", description="Test command")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message("Pong!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(General(bot))
