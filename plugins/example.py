from discord.ext import commands
from discord import app_commands
import discord

class Example(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="hello", description="Say hello from the example plugin")
    async def hello(self, interaction: discord.Interaction):
        await interaction.response.send_message("👋 Hello from the example plugin!")

async def setup(bot: commands.Bot):
    await bot.add_cog(Example(bot))
