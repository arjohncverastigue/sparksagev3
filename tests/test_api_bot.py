from fastapi.testclient import TestClient
from api.main import create_app
import bot as bot_module


def override_get_current_user():
    # simple stub for auth dependency
    return {"username": "tester", "role": "admin"}


def test_list_guild_channels_no_guild(monkeypatch):
    app = create_app()
    # override auth dependency
    app.dependency_overrides.clear()
    from api.deps import get_current_user
    app.dependency_overrides[get_current_user] = lambda: override_get_current_user()

    client = TestClient(app)
    # ensure bot.get_guild returns None
    monkeypatch.setattr(bot_module.bot, "get_guild", lambda x: None)
    resp = client.get("/api/bot/guilds/999/channels")
    assert resp.status_code == 200
    data = resp.json()
    assert data == {"channels": []}


def test_list_guild_channels_with_data(monkeypatch):
    app = create_app()
    app.dependency_overrides.clear()
    from api.deps import get_current_user
    app.dependency_overrides[get_current_user] = lambda: override_get_current_user()
    client = TestClient(app)

    class DummyGuild:
        def __init__(self, channels):
            self.text_channels = channels

    class DummyChannel:
        def __init__(self, id, name):
            self.id = id
            self.name = name

    dummy_channels = [DummyChannel(1, "general"), DummyChannel(2, "random")]
    monkeypatch.setattr(bot_module.bot, "get_guild", lambda x: DummyGuild(dummy_channels))

    resp = client.get("/api/bot/guilds/123/channels")
    assert resp.status_code == 200
    data = resp.json()
    assert "channels" in data
    assert isinstance(data["channels"], list)
    assert any(c["name"] == "general" for c in data["channels"])
    # invalid guild id should not crash
    resp2 = client.get("/api/bot/guilds/not_a_number/channels")
    assert resp2.status_code == 200
    assert resp2.json() == {"channels": []}
