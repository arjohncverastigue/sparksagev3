import discord
from discord.ext import commands
from discord import app_commands
import random

TRIVIA_QUESTIONS = [
    {
        "question": "What is the capital of France?",
        "answer": "paris",
        "choices": ["London", "Berlin", "Paris", "Rome"]
    },
    {
        "question": "How many sides does a hexagon have?",
        "answer": "6",
        "choices": ["5", "6", "7", "8"]
    },
    {
        "question": "What planet is known as the Red Planet?",
        "answer": "mars",
        "choices": ["Venus", "Jupiter", "Mars", "Saturn"]
    },
]


class Trivia(commands.Cog):
    """A sample trivia plugin for testing the plugin system."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_games: dict[int, dict] = {}  # channel_id -> question data

    @app_commands.command(name="trivia", description="Start a trivia question!")
    async def trivia(self, interaction: discord.Interaction):
        channel_id = interaction.channel_id

        if channel_id in self.active_games:
            await interaction.response.send_message(
                "⚠️ A trivia game is already active in this channel!", ephemeral=True
            )
            return

        q = random.choice(TRIVIA_QUESTIONS)
        self.active_games[channel_id] = q

        choices_text = "\n".join(
            f"{i+1}. {c}" for i, c in enumerate(q["choices"])
        )

        embed = discord.Embed(
            title="🧠 Trivia Time!",
            description=f"**{q['question']}**\n\n{choices_text}",
            color=discord.Color.blurple(),
        )
        embed.set_footer(text="Use /answer <your answer> to respond!")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="answer", description="Answer the current trivia question.")
    @app_commands.describe(response="Your answer to the trivia question")
    async def answer(self, interaction: discord.Interaction, response: str):
        channel_id = interaction.channel_id

        if channel_id not in self.active_games:
            await interaction.response.send_message(
                "❌ No active trivia game in this channel. Use /trivia to start one!",
                ephemeral=True,
            )
            return

        q = self.active_games[channel_id]
        correct = response.strip().lower() == q["answer"].lower()

        if correct:
            del self.active_games[channel_id]
            await interaction.response.send_message(
                f"✅ **Correct!** Well done, {interaction.user.mention}! "
                f"The answer was **{q['answer'].capitalize()}**."
            )
        else:
            await interaction.response.send_message(
                f"❌ **Wrong!** Try again, {interaction.user.mention}.", ephemeral=True
            )

    @app_commands.command(name="trivia_skip", description="Skip the current trivia question.")
    async def trivia_skip(self, interaction: discord.Interaction):
        channel_id = interaction.channel_id

        if channel_id not in self.active_games:
            await interaction.response.send_message(
                "❌ No active trivia game to skip.", ephemeral=True
            )
            return

        q = self.active_games.pop(channel_id)
        await interaction.response.send_message(
            f"⏭️ Skipped! The correct answer was **{q['answer'].capitalize()}**."
        )


async def setup(bot: commands.Bot):
    """Entry point called by the plugin loader."""
    await bot.add_cog(Trivia(bot))
