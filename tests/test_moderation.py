import pytest
import json
from cogs.moderation import Moderation


class DummyMessage:
    def __init__(self, content):
        self.content = content
        self.author = type("A", (), {"bot": False, "id": 1, "display_name": "User"})
        class Guild:
            id = 123
        class Channel:
            id = 456
        self.guild = Guild()
        self.channel = Channel()
        self.id = 789
        self.jump_url = "http://example.com"

class DummyBot:
    async def ask_ai(self, channel_id, user_name, message, system_prompt=None, message_type=None):
        # default stub; can be replaced
        return "{\"flagged\": false, \"reason\": \"\", \"severity\": \"low\"}", "provider"

@pytest.mark.asyncio
async def test_moderation_valid(monkeypatch, capsys):
    bot = DummyBot()
    cog = Moderation(bot)
    msg = DummyMessage("hello world")
    # ensure config enabled
    import config
    config.MODERATION_ENABLED = True

    await cog.check_message_for_moderation(msg)
    captured = capsys.readouterr()
    # no errors printed
    assert "invalid JSON" not in captured.out

@pytest.mark.asyncio
async def test_moderation_invalid_json(monkeypatch, capsys):
    bot = DummyBot()
    async def bad_ask_ai(channel_id, user_name, message, system_prompt=None, message_type=None):
        return "not a json", "provider"
    bot.ask_ai = bad_ask_ai
    cog = Moderation(bot)
    msg = DummyMessage("bad content")
    import config
    config.MODERATION_ENABLED = True

    await cog.check_message_for_moderation(msg)
    captured = capsys.readouterr()
    assert "Moderation AI returned invalid JSON" in captured.out
