import os
import pytest
import db

# simple database tests for plugin helpers
@pytest.mark.asyncio
async def test_plugin_db_helpers(tmp_path):
    db_path = tmp_path / "test.db"
    os.environ["DATABASE_PATH"] = str(db_path)
    # initialize database (creates all tables, including plugins)
    await db.init_db()

    # verify no plugins initially
    plugins = await db.list_plugins()
    assert plugins == [], "should start with an empty plugins table"

    # upsert a fake manifest
    manifest = {
        "name": "fake",
        "version": "1.2.3",
        "author": "tester",
        "description": "a fake plugin",
    }
    await db.upsert_plugin(manifest, "/fake/cog.py", "/fake/manifest.json")

    info = await db.get_plugin("fake")
    assert info is not None
    assert info["name"] == "fake"
    assert info["version"] == "1.2.3"
    assert info["author"] == "tester"
    assert info["description"] == "a fake plugin"
    assert info["cog_path"] == "/fake/cog.py"
    assert info["manifest_path"] == "/fake/manifest.json"
    assert info["enabled"] == 0

    # list_plugins should include it
    all_plugins = await db.list_plugins()
    assert len(all_plugins) == 1 and all_plugins[0]["name"] == "fake"

    # toggle enabled flag
    await db.set_plugin_enabled("fake", True)
    info2 = await db.get_plugin("fake")
    assert info2["enabled"] == 1
    await db.set_plugin_enabled("fake", False)
    info3 = await db.get_plugin("fake")
    assert info3["enabled"] == 0
