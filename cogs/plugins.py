import discord
from discord import app_commands
from discord import Interaction

import plugins as plugin_module
import db

plugin_group = app_commands.Group(name="plugin", description="Manage bot plugins")


@plugin_group.command(name="list", description="List available plugins")
async def plugin_list(interaction: Interaction):
    await interaction.response.defer()
    rows = await db.list_plugins()
    if not rows:
        await interaction.followup.send("No plugins found.")
        return
    lines = []
    for p in rows:
        status = "✅ enabled" if p.get("enabled") else "⚪ disabled"
        lines.append(f"**{p['name']}** {status} - {p.get('description','')}")
    await interaction.followup.send("\n".join(lines))


@plugin_group.command(name="enable", description="Enable a plugin")
@app_commands.describe(name="Plugin name as defined in manifest")
async def plugin_enable(interaction: Interaction, name: str):
    # only bot owner may enable plugins
    is_owner = await interaction.client.is_owner(interaction.user)
    if not is_owner:
        await interaction.response.send_message("Only the bot owner may enable plugins.", ephemeral=True)
        return

    await interaction.response.defer()
    success = await plugin_module.enable_plugin(interaction.client, name)
    if success:
        await interaction.followup.send(f"Plugin **{name}** enabled.")
    else:
        await interaction.followup.send(f"Failed to enable plugin **{name}**. Is the manifest correct?", ephemeral=True)


@plugin_group.command(name="disable", description="Disable a plugin")
@app_commands.describe(name="Plugin name as defined in manifest")
async def plugin_disable(interaction: Interaction, name: str):
    # only bot owner may disable plugins
    is_owner = await interaction.client.is_owner(interaction.user)
    if not is_owner:
        await interaction.response.send_message("Only the bot owner may disable plugins.", ephemeral=True)
        return

    await interaction.response.defer()
    success = await plugin_module.disable_plugin(interaction.client, name)
    if success:
        await interaction.followup.send(f"Plugin **{name}** disabled.")
    else:
        await interaction.followup.send(f"Failed to disable plugin **{name}**. Is it loaded?", ephemeral=True)


async def setup(bot):
    # register the command group with the bot's application command tree
    bot.tree.add_command(plugin_group)
 