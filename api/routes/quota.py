from fastapi import APIRouter, Depends
from api.deps import get_current_user
from bot import bot

router = APIRouter()


@router.get("/status")
async def get_quota_status(user: dict = Depends(get_current_user)):
    """Get current rate limiting quotas for all users and guilds."""
    if not hasattr(bot, "rate_limiter"):
        return {"error": "Rate limiting not enabled"}

    quotas = bot.rate_limiter.get_all_quotas()
    return {
        "rate_limit_user": bot.rate_limiter.user_capacity,
        "rate_limit_guild": bot.rate_limiter.guild_capacity,
        "quotas": quotas,
    }
