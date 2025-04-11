from discord.ext import commands
from discord import app_commands, Interaction

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot



async def setup(bot: commands.Bot):
    general = General(bot)
    await bot.add_cog(general)

