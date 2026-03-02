from __future__ import annotations

import discord
from discord.ext import commands
import time
import asyncio

import config
import providers
import db as database
from utils.rate_limiter import RateLimiter
import plugins

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class SparkSageBot(commands.Bot):
    def __init__(self, command_prefix, intents):
        super().__init__(command_prefix=command_prefix, intents=intents)
        self.MAX_HISTORY = 20

    async def get_history(self, channel_id: int) -> list[dict]:
        """Get conversation history for a channel from the database."""
        messages = await database.get_messages(str(channel_id), limit=self.MAX_HISTORY)
        return [{"role": m["role"], "content": m["content"]} for m in messages]

    async def ask_ai(
        self,
        channel_id: int,
        user_name: str,
        message: str,
        system_prompt: str = None,
        message_type: str | None = None,
    ) -> tuple[str, str]:
        """Send a message to AI and return (response, provider_name).

        ``message_type`` is an arbitrary tag (e.g. "command", "mention", "translation",
        etc.) that will be recorded in analytics.
        """
        # Store user message in DB
        await database.add_message(str(channel_id), "user", user_name, message, type=message_type)

        # Get guild_id from channel for rate limiting
        guild_id = None
        chan = self.get_channel(int(channel_id)) if channel_id else None
        if chan and hasattr(chan, "guild") and chan.guild:
            guild_id = str(chan.guild.id)

        # Check rate limit
        if config.RATE_LIMITING_ENABLED and hasattr(self, "rate_limiter"):
            allowed, reason = self.rate_limiter.is_allowed(user_name, guild_id)
            if not allowed:
                return f"⏱️ Rate limited: {reason}", "none"

        history = await self.get_history(channel_id)

        # Get channel-specific system prompt if available
        channel_system_prompt = await database.get_channel_prompt(str(channel_id))
        final_system_prompt = system_prompt or channel_system_prompt or config.SYSTEM_PROMPT

        # Get channel-specific provider if available
        channel_provider_override = await database.get_channel_provider(str(channel_id))

        # Measure latency for analytics
        start = time.time()
        try:
            # providers.chat is a blocking, synchronous call (uses HTTP clients).
            # Run it in a thread to avoid blocking the bot's asyncio event loop.
            response, provider_name, input_toks, output_toks, total_toks = await asyncio.to_thread(
                providers.chat, history, final_system_prompt, channel_provider_override
            )
            latency_ms = int((time.time() - start) * 1000)
            # Store assistant response in DB
            await database.add_message(
                str(channel_id),
                "assistant",
                self.user.display_name,
                response,
                provider=provider_name,
                type=message_type,
            )

            # estimate cost based on configured pricing (dollars per 1k tokens)
            price_per_1k = config.PROVIDERS.get(provider_name, {}).get("price_per_1k_tokens", 0) or 0
            estimated_cost = (total_toks / 1000) * price_per_1k

            # record analytics event including token usage and cost
            await database.add_analytics_event(
                event_type=message_type or "ai_call",
                guild_id=guild_id,
                channel_id=str(channel_id),
                user_id=user_name,
                provider=provider_name,
                tokens_used=total_toks,
                input_tokens=input_toks,
                output_tokens=output_toks,
                estimated_cost=estimated_cost,
                latency_ms=latency_ms,
            )

            return response, provider_name

        except RuntimeError as e:
            return f"Sorry, all AI providers failed:\n{e}", "none"

    async def setup_hook(self):
        # Load cogs here
        await self.load_extension("cogs.general")
        await self.load_extension("cogs.summarize")
        await self.load_extension("cogs.code_review")
        await self.load_extension("cogs.faq")
        await self.load_extension("cogs.onboarding")
        await self.load_extension("cogs.permissions")
        await self.load_extension("cogs.digest")
        await self.load_extension("cogs.moderation")
        await self.load_extension("cogs.translate")
        await self.load_extension("cogs.channel_prompts")
        await self.load_extension("cogs.channel_providers")
        # management cog for enabling/disabling plugins
        await self.load_extension("cogs.plugins")
        # load any community plugins
        await plugins.load_plugins(self)


bot = SparkSageBot(command_prefix=config.BOT_PREFIX, intents=intents)

# Initialize rate limiter
if config.RATE_LIMITING_ENABLED:
    bot.rate_limiter = RateLimiter(
        user_rate=config.RATE_LIMIT_USER,
        guild_rate=config.RATE_LIMIT_GUILD,
    )


def get_bot_status() -> dict:
    """Return bot status info for the dashboard API."""
    if bot.is_ready():
        return {
            "online": True,
            "username": str(bot.user),
            "latency_ms": round(bot.latency * 1000, 1),
            "guild_count": len(bot.guilds),
            "guilds": [{"id": str(g.id), "name": g.name, "member_count": g.member_count} for g in bot.guilds],
        }
    return {"online": False, "username": None, "latency_ms": None, "guild_count": 0, "guilds": []}


# --- Events ---


@bot.event
async def on_ready():
    # Initialize database when bot is ready
    await database.init_db()
    await database.sync_env_to_db()

    available = providers.get_available_providers()
    primary = config.AI_PROVIDER
    provider_info = config.PROVIDERS.get(primary, {})

    print(f"SparkSage is online as {bot.user}")
    print(f"Primary provider: {provider_info.get('name', primary)} ({provider_info.get('model', '?')})")
    print(f"Fallback chain: {' -> '.join(available)}")

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")


@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    moderation_cog = bot.get_cog("Moderation")
    if moderation_cog:
        await moderation_cog.check_message_for_moderation(message)
    
    # Respond when mentioned
    if bot.user in message.mentions:
        clean_content = message.content.replace(f"<@{bot.user.id}>", "").strip()
        if not clean_content:
            clean_content = "Hello!"

        async with message.channel.typing():
            response, provider_name = await bot.ask_ai(
                message.channel.id,
                message.author.display_name,
                clean_content,
                message_type="mention",
            )

        # Split long responses (Discord 2000 char limit)
        for i in range(0, len(response), 2000):
            await message.reply(response[i : i + 2000])

    await bot.process_commands(message)


# --- Run ---


def main():
    if not config.DISCORD_TOKEN:
        print("Error: DISCORD_TOKEN not set. Copy .env.example to .env and fill in your tokens.")
        return

    available = providers.get_available_providers()
    if not available:
        print("Error: No AI providers configured. Add at least one API key to .env")
        print("Free options: GEMINI_API_KEY, GROQ_API_KEY, or OPENROUTER_API_KEY")
        return

    bot.run(config.DISCORD_TOKEN)


if __name__ == "__main__":
    main()
