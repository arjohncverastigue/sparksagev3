import time
from fastapi import APIRouter, Depends, HTTPException, status
from api.deps import get_current_user
import bot

router = APIRouter()

@router.get("/status")
async def get_quota_status(user: dict = Depends(get_current_user)):
    if not hasattr(bot.bot, "rate_limiter"):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Rate limiter not initialized.")
    
    rate_limiter = bot.bot.rate_limiter
    
    users_quotas = {}
    for user_id in rate_limiter.user_buckets.keys():
        quota_info = rate_limiter.get_user_quota(user_id)
        users_quotas[user_id] = {
            "tokens_remaining": quota_info["remaining"],
            "reset_at": time.time() + quota_info["reset_in_seconds"],
        }
    
    guilds_quotas = {}
    for guild_id in rate_limiter.guild_buckets.keys():
        quota_info = rate_limiter.get_guild_quota(guild_id)
        guilds_quotas[guild_id] = {
            "tokens_remaining": quota_info["remaining"],
            "reset_at": time.time() + quota_info["reset_in_seconds"],
        }

    return {
        "rate_limit_user": rate_limiter.user_capacity,
        "rate_limit_guild": rate_limiter.guild_capacity,
        "quotas": {
            "users": users_quotas,
            "guilds": guilds_quotas,
        },
    }

@router.get("/quotas")
async def get_all_quotas(user: dict = Depends(get_current_user)):
    if not hasattr(bot.bot, "rate_limiter"):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Rate limiter not initialized.")
    
    return bot.bot.rate_limiter.get_all_quotas()

@router.get("/quotas/user/{user_id}")
async def get_user_quota(user_id: str, user: dict = Depends(get_current_user)):
    if not hasattr(bot.bot, "rate_limiter"):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Rate limiter not initialized.")
    
    return bot.bot.rate_limiter.get_user_quota(user_id)

@router.get("/quotas/guild/{guild_id}")
async def get_guild_quota(guild_id: str, user: dict = Depends(get_current_user)):
    if not hasattr(bot.bot, "rate_limiter"):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Rate limiter not initialized.")
    
    return bot.bot.rate_limiter.get_guild_quota(guild_id)
