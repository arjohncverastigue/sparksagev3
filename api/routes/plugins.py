from fastapi import APIRouter, Depends, HTTPException
from api.deps import get_current_user
import db
from bot import bot
import plugins as plugin_module

router = APIRouter()


@router.get("")
async def list_plugins(user: dict = Depends(get_current_user)):
    """List all discovered plugins and their enabled/disabled state."""
    rows = await db.list_plugins()
    return {"plugins": rows}


@router.post("/{name}/enable")
async def enable_plugin(name: str, user: dict = Depends(get_current_user)):
    """Enable a plugin at runtime."""
    success = await plugin_module.enable_plugin(bot, name)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to enable plugin")
    return {"status": "ok"}


@router.post("/{name}/disable")
async def disable_plugin(name: str, user: dict = Depends(get_current_user)):
    """Disable a plugin at runtime."""
    success = await plugin_module.disable_plugin(bot, name)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to disable plugin")
    return {"status": "ok"}
