import os
import shutil
import zipfile  # New import
import tempfile # New import
from typing import List

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from api.deps import get_current_user
from loguru import logger
import db # Import db

# Import PLUGINS_DIR and the new scan_and_persist_plugin_metadata function
from plugins import PLUGINS_DIR, scan_and_persist_plugin_metadata

router = APIRouter()

@router.get("")
@router.get("/")
async def get_all_plugins(
    user: dict = Depends(get_current_user)
):
    plugins_data = await db.list_plugins()
    return {"plugins": plugins_data}

@router.post("/upload")
async def upload_plugin(
    plugin_zip_file: UploadFile = File(...), # Changed to single UploadFile
    user: dict = Depends(get_current_user)
):
    """
    Uploads a plugin as a ZIP archive, extracts its contents, and moves
    the manifest.json and .py file to the plugins directory.
    """
    if not plugin_zip_file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .zip files are allowed for plugin uploads."
        )

    # Create a temporary directory to extract the zip contents
    with tempfile.TemporaryDirectory() as temp_dir:
        zip_file_path = os.path.join(temp_dir, plugin_zip_file.filename)
        
        # Save the uploaded zip file to the temporary directory
        try:
            with open(zip_file_path, "wb") as buffer:
                shutil.copyfileobj(plugin_zip_file.file, buffer)
            logger.info(f"Saved uploaded zip file to {zip_file_path}")
        except Exception as e:
            logger.error(f"Failed to save uploaded zip file: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save uploaded zip file: {e}"
            )

        # Extract the zip file
        try:
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            logger.info(f"Extracted zip file contents to {temp_dir}")
        except zipfile.BadZipFile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid ZIP file provided."
            )
        except Exception as e:
            logger.error(f"Failed to extract zip file: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to extract zip file: {e}"
            )

        # Scan for manifest.json and .py files in the extracted directory
        manifest_path = None
        plugin_py_path = None
        for root, _, files in os.walk(temp_dir):
            for file in files:
                if file == "manifest.json":
                    manifest_path = os.path.join(root, file)
                elif file.endswith(".py"):
                    plugin_py_path = os.path.join(root, file)

        if not manifest_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Plugin ZIP archive must contain a 'manifest.json' file."
            )
        if not plugin_py_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Plugin ZIP archive must contain a '.py' plugin file."
            )

        # Ensure the plugins directory exists
        os.makedirs(PLUGINS_DIR, exist_ok=True)

        uploaded_filenames = []
        try:
            # Move manifest.json
            final_manifest_path = os.path.join(PLUGINS_DIR, os.path.basename(manifest_path))
            shutil.copy2(manifest_path, final_manifest_path) # Use copy2 instead of move
            os.remove(manifest_path) # Remove original
            uploaded_filenames.append(os.path.basename(final_manifest_path))
            logger.info(f"Moved manifest.json to {final_manifest_path}")

            # Move .py file
            final_py_path = os.path.join(PLUGINS_DIR, os.path.basename(plugin_py_path))
            shutil.copy2(plugin_py_path, final_py_path) # Use copy2 instead of move
            os.remove(plugin_py_path) # Remove original
            uploaded_filenames.append(os.path.basename(final_py_path))
            logger.info(f"Moved plugin .py file to {final_py_path}")
        except Exception as e:
            logger.error(f"Failed to move extracted plugin files: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to move extracted plugin files: {e}"
            )
    
    # After uploading files, trigger a scan to discover them and persist metadata
    await scan_and_persist_plugin_metadata()

    return {
        "message": f"Successfully uploaded plugin from {plugin_zip_file.filename} and initiated plugin scan.",
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

