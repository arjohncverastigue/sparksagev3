from fastapi import APIRouter, Depends
from api.deps import get_current_user

router = APIRouter()


@router.get("/status")
async def bot_status(user: dict = Depends(get_current_user)):
    from bot import get_bot_status
    return get_bot_status()


@router.get("/guilds/{guild_id}/channels")
async def list_guild_channels(guild_id: str, user: dict = Depends(get_current_user)):
    """Return list of channels for the specified guild using the running bot.

    If the guild_id cannot be converted to an integer or the bot doesn't know the
    guild, simply return an empty list instead of raising a server error. This
    makes the frontend more forgiving (e.g. placeholder values).
    """
    from bot import bot

    guild = None
    if bot and guild_id:
        try:
            gid_int = int(guild_id)
            guild = bot.get_guild(gid_int)
        except ValueError:
            # invalid snowflake string
            guild = None
    if not guild:
        return {"channels": []}

    channels = []
    for ch in guild.text_channels:
        channels.append({"id": str(ch.id), "name": ch.name})
    return {"channels": channels}
