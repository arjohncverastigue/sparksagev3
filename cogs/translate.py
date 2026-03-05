import discord
from discord.ext import commands
from discord import app_commands # Import app_commands
import config
import asyncio # For rate limiting

# Cooldown for auto-translations per channel
AUTO_TRANSLATE_COOLDOWN = commands.CooldownMapping.from_cooldown(
    1, 10.0, commands.BucketType.channel
)

class Translate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="translate", description="Translate text to a target language.")
    @app_commands.describe(text="The text to translate", target_language="The language to translate to (e.g., 'French', 'es', 'Japanese')")
    async def translate_command(self, interaction: discord.Interaction, text: str, target_language: str):
        await interaction.response.defer()

        # Use the existing AI provider for translation
        translation_prompt = f"""Translate the following text to {target_language}. Respond only with the translated text, without any additional conversational filler.

Text to translate: "{text}"
"""

        try:
            translated_text, _ = await self.bot.ask_ai(
                channel_id=interaction.channel_id,
                user_name=interaction.user.display_name,
                message=translation_prompt,
                system_prompt="You are a helpful translation assistant. Provide only the translation.",
                message_type="translation"
            )
            await interaction.followup.send(f"""**Original ({text}) translated to {target_language}:**
{translated_text}""")
        except Exception as e:
            await interaction.followup.send(f"An error occurred during translation: {e}")
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if not config.AUTO_TRANSLATE_ENABLED:
            return
        
        # Check if the channel is designated for auto-translation
        if message.channel.id not in config.AUTO_TRANSLATE_CHANNELS:
            return

        # Apply cooldown to prevent spamming
        bucket = AUTO_TRANSLATE_COOLDOWN.get_bucket(message)
        if bucket.update_rate_limit():
            return

        # Use AI to detect language and translate if not default
        detection_and_translation_prompt = f"""Detect the language of the following text.
If the detected language is not "{config.DEFAULT_TRANSLATION_LANGUAGE}", translate the text to "{config.DEFAULT_TRANSLATION_LANGUAGE}".
Respond in a structured format:
Detected Language: <detected_language_name>
Translated Text: <translated_text> (Only if translation occurred)
If no translation occurred, omit "Translated Text:"

Text: "{message.content}"
"""

        try:
            ai_response, _ = await self.bot.ask_ai(
                channel_id=message.channel.id,
                user_name=message.author.display_name,
                message=detection_and_translation_prompt,
                system_prompt="You are a language detection and translation assistant. Follow the user's instructions precisely.",
                message_type="auto_translation"
            )
            
            detected_language = "Unknown"
            translated_text = None

            # Parse the AI's structured response
            lines = ai_response.split('\n')
            for line in lines:
                if line.startswith("Detected Language:"):
                    detected_language = line.split(":", 1)[1].strip()
                elif line.startswith("Translated Text:"):
                    translated_text = line.split(":", 1)[1].strip()
            
            if translated_text:
                # Avoid translating if the detected language is already the default
                # This is a fallback in case AI misinterpreted the prompt and translated anyway
                if detected_language.lower() != config.DEFAULT_TRANSLATION_LANGUAGE.lower():
                    await message.reply(
                        f"Detected language: `{detected_language}`. "
                        f"Translated to {config.DEFAULT_TRANSLATION_LANGUAGE}:\n{translated_text}"
                    )
            elif detected_language.lower() != config.DEFAULT_TRANSLATION_LANGUAGE.lower():
                 # If no translated text but language is different, inform (optional)
                 pass
                # await message.reply(f"Detected language: `{detected_language}`. No translation performed as it was requested only if not {config.DEFAULT_TRANSLATION_LANGUAGE}.")


        except Exception as e:
            print(f"Error during auto-translation: {e}")
        
        await self.bot.process_commands(message) # Important to process other commands too


async def setup(bot):
    await bot.add_cog(Translate(bot))