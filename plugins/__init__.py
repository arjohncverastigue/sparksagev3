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
            except Exception:
                continue
            slug = data.get("name") or os.path.splitext(entry)[0]
            manifests[slug] = {**data, "__manifest_path": path}
    return manifests


async def load_plugins(bot: commands.Bot):
    """Scan plugin manifests, persist metadata, and load enabled cogs."""
    manifests = _scan_manifests()
    for slug, manifest in manifests.items():
        # determine cog filename from manifest
        cog_file = manifest.get("cog")
        if not cog_file:
            continue
        cog_path = os.path.join(PLUGINS_DIR, cog_file)
        # persist metadata to DB
        await upsert_plugin(manifest, cog_path, manifest.get("__manifest_path", ""))
        # check enabled flag
        entry = await get_plugin(slug)
        if entry and entry.get("enabled"):
            module_name = f"plugins.{os.path.splitext(cog_file)[0]}"
            try:
                await bot.load_extension(module_name)
                print(f"Loaded plugin {slug} ({module_name})")
            except Exception as e:
                print(f"Failed loading plugin {slug}: {e}")


async def enable_plugin(bot: commands.Bot, name: str) -> bool:
    """Enable a plugin by name (slug) at runtime."""
    manifests = _scan_manifests()
    if name not in manifests:
        return False
    manifest = manifests[name]
    cog_file = manifest.get("cog")
    if not cog_file:
        return False
    module_name = f"plugins.{os.path.splitext(cog_file)[0]}"
    try:
        await bot.load_extension(module_name)
    except commands.ExtensionAlreadyLoaded:
        # already loaded is fine
        pass
    except Exception:
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
    except commands.ExtensionNotLoaded:
        # nothing to unload
        pass
    except Exception:
        pass
    await set_plugin_enabled(name, False)
    return True
