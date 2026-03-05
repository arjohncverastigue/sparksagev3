import os
import shutil
from typing import List

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from api.deps import get_current_user
from loguru import logger
import db # Import db

# Import PLUGINS_DIR and the new scan_and_persist_plugin_metadata function
from plugins import PLUGINS_DIR, scan_and_persist_plugin_metadata

router = APIRouter()

@router.get("/")
async def get_all_plugins(
    user: dict = Depends(get_current_user)
):
    """
    Returns a list of all discovered plugins with their status.
    """
    plugins_data = await db.list_plugins()
    return {"plugins": plugins_data}

@router.post("/upload")
async def upload_plugin(
    plugin_files: List[UploadFile],
    user: dict = Depends(get_current_user)
):
    """
    Uploads plugin files (manifest.json and cog.py) to the plugins directory.
    """
    if not plugin_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided for upload."
        )

    uploaded_filenames = []
    for uploaded_file in plugin_files:
        file_extension = os.path.splitext(uploaded_file.filename)[1].lower()
        if file_extension not in (".json", ".py"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Only .json and .py files are allowed. Received: {uploaded_file.filename}"
            )

        file_path = os.path.join(PLUGINS_DIR, uploaded_file.filename)
        
        try:
            # Ensure the plugins directory exists
            os.makedirs(PLUGINS_DIR, exist_ok=True)
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(uploaded_file.file, buffer)
            uploaded_filenames.append(uploaded_file.filename)
            logger.info(f"Uploaded plugin file: {uploaded_file.filename}")
        except Exception as e:
            logger.error(f"Failed to upload {uploaded_file.filename}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload {uploaded_file.filename}: {e}"
            )
    
    # After uploading files, trigger a scan to discover them and persist metadata
    await scan_and_persist_plugin_metadata()

    return {
        "message": f"Successfully uploaded files: {', '.join(uploaded_filenames)} and initiated plugin scan.",
        "filenames": uploaded_filenames
    }

@router.post("/rescan")
async def rescan_plugins_endpoint(
    user: dict = Depends(get_current_user)
):
    """
    Triggers a re-scan of the plugins directory to discover new plugins
    and updates their status in the database.
    """
    logger.info("API endpoint /plugins/rescan triggered.")
    await scan_and_persist_plugin_metadata()
    return {"message": "Plugin directory scan initiated successfully. Check plugin list for updates."}

@router.delete("/{name}")
async def delete_plugin(
    name: str,
    user: dict = Depends(get_current_user)
):
    """
    Deletes a plugin by name, including its database entry and files.
    """
    # Ensure the plugin is disabled before deleting files if it's currently loaded
    # (This logic is outside the scope of this API endpoint, should be handled by bot if needed)

    # First, get the paths and delete from DB
    cog_path, manifest_path = await db.delete_plugin_by_name(name)

    if cog_path is None and manifest_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin '{name}' not found."
        )
    
    deleted_files = []
    # Delete cog file
    if cog_path and os.path.exists(cog_path):
        try:
            os.remove(cog_path)
            deleted_files.append(os.path.basename(cog_path))
            logger.info(f"Deleted plugin cog file: {cog_path}")
        except Exception as e:
            logger.error(f"Failed to delete cog file {cog_path}: {e}")

    # Delete manifest file
    if manifest_path and os.path.exists(manifest_path):
        try:
            os.remove(manifest_path)
            deleted_files.append(os.path.basename(manifest_path))
            logger.info(f"Deleted plugin manifest file: {manifest_path}")
        except Exception as e:
            logger.error(f"Failed to delete manifest file {manifest_path}: {e}")

    # It's good practice to re-scan after file deletion to clean up any inconsistencies
    await scan_and_persist_plugin_metadata()

    message = f"Plugin '{name}' deleted successfully."
    if deleted_files:
        message += f" Deleted files: {', '.join(deleted_files)}"

    return {"message": message}

@router.post("/{name}/enable")
async def enable_plugin(
    name: str,
    user: dict = Depends(get_current_user)
):
    """
    Enables a plugin by name.
    """
    import bot
    import plugins

    if not hasattr(bot.bot, "is_ready") or not bot.bot.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Discord bot is not running or ready yet."
        )

    try:
        success = await plugins.enable_plugin(bot.bot, name)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plugin '{name}' not found or could not be enabled."
            )
        return {"status": "success", "message": f"Plugin '{name}' enabled and loaded."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enable plugin '{name}': {e}"
        )

@router.post("/{name}/disable")
async def disable_plugin(
    name: str,
    user: dict = Depends(get_current_user)
):
    """
    Disables a plugin by name.
    """
    import bot
    import plugins

    if not hasattr(bot.bot, "is_ready") or not bot.bot.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Discord bot is not running or ready yet."
        )

    try:
        success = await plugins.disable_plugin(bot.bot, name)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plugin '{name}' not found or could not be disabled."
            )
        return {"status": "success", "message": f"Plugin '{name}' disabled."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disable plugin '{name}': {e}"
        )

