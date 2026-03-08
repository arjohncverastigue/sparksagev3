import os
import json
from typing import Dict

from discord.ext import commands

from db import upsert_plugin, get_plugin, set_plugin_enabled

# directory containing plugin manifests and cog files
PLUGINS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__)))


def _scan_manifests() -> Dict[str, dict]:
    """Return a map of plugin slug -> manifest data from JSON files."""
    manifests: Dict[str, dict] = {}
    if not os.path.isdir(PLUGINS_DIR):
        os.makedirs(PLUGINS_DIR, exist_ok=True)
    for entry in os.listdir(PLUGINS_DIR):
        if entry.endswith(".json"):
            path = os.path.join(PLUGINS_DIR, entry)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                # Log the error but continue scanning other files
                print(f"Error reading or parsing plugin manifest {path}: {e}")
                continue
            slug = data.get("name") or os.path.splitext(entry)[0]
            manifests[slug] = {**data, "__manifest_path": path}
    return manifests

async def scan_and_persist_plugin_metadata():
    """
    Scans plugin manifests and persists their metadata to the database.
    Does NOT load cogs.
    """
    print("Scanning plugin manifests and persisting metadata...")
    manifests = _scan_manifests()
    for slug, manifest in manifests.items():
        cog_file = manifest.get("cog")
        
        # Ensure cog_file is specified in manifest
        if not cog_file:
            print(f"Warning: Plugin '{slug}' manifest '{manifest.get('__manifest_path')}' is missing 'cog' field. Skipping.")
            continue
            
        cog_path = os.path.join(PLUGINS_DIR, cog_file)
        
        # Ensure cog_file actually exists on disk
        if not os.path.exists(cog_path):
            print(f"Warning: Plugin '{slug}' cog file '{cog_file}' not found at '{cog_path}'. Skipping.")
            continue

        await upsert_plugin(manifest, cog_path, manifest.get("__manifest_path", ""))
    print("Plugin metadata scan complete.")


async def load_plugins(bot: commands.Bot):
    """Scan plugin manifests, persist metadata, and load enabled cogs."""
    # First, scan and persist all metadata, regardless of enabled status
    await scan_and_persist_plugin_metadata()

    # Then, load only the enabled cogs
    manifests = _scan_manifests() # Re-scan to get potentially new metadata if just added
    for slug, manifest in manifests.items():
        # determine cog filename from manifest
        cog_file = manifest.get("cog")
        if not cog_file:
            continue
        # check enabled flag from DB
        entry = await get_plugin(slug)
        if entry and entry.get("enabled"):
            module_name = f"plugins.{os.path.splitext(cog_file)[0]}"
            try:
                await bot.load_extension(module_name)
                print(f"Loaded plugin {slug} ({module_name})")
            except commands.ExtensionAlreadyLoaded:
                # This can happen if the bot reconnects or load_plugins is called multiple times
                print(f"Plugin {slug} ({module_name}) already loaded.")
                pass
            except Exception as e:
                print(f"Failed loading plugin {slug}: {e}")


async def enable_plugin(bot: commands.Bot, name: str) -> bool:
    """Enable a plugin by name (slug) at runtime."""
    manifests = _scan_manifests()
    if name not in manifests:
        # Before returning False, try to rescan manifests in case it's a newly added file
        await scan_and_persist_plugin_metadata()
        manifests = _scan_manifests() # Re-scan again
        if name not in manifests:
            return False

    manifest = manifests[name]
    cog_file = manifest.get("cog")
    if not cog_file:
        return False
    module_name = f"plugins.{os.path.splitext(cog_file)[0]}"
    try:
        await bot.load_extension(module_name)
        # Sync slash commands with Discord after loading a new extension
        await bot.tree.sync()
    except commands.ExtensionAlreadyLoaded:
        # already loaded is fine
        pass
    except Exception as e:
        print(f"Failed to enable plugin {name}: {e}")
        return False
    await set_plugin_enabled(name, True)
    return True


async def disable_plugin(bot: commands.Bot, name: str) -> bool:
    """Disable a plugin by name at runtime."""
    manifests = _scan_manifests()
    if name not in manifests:
        return False
    manifest = manifests[name]
    cog_file = manifest.get("cog")
    if not cog_file:
        return False
    module_name = f"plugins.{os.path.splitext(cog_file)[0]}"
    try:
        await bot.unload_extension(module_name)
        # Sync slash commands with Discord after unloading an extension
        await bot.tree.sync()
    except commands.ExtensionNotLoaded:
        # nothing to unload
        pass
    except Exception as e:
        print(f"Failed to disable plugin {name}: {e}")
        pass # Allow disabling even if unload fails, to update DB status
    await set_plugin_enabled(name, False)
    return True
