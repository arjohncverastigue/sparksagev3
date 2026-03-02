import pytest

from cogs.code_review import CodeReview


class DummyFollowup:
    def __init__(self):
        self.sent = []

    async def send(self, content):
        # record sent content for verification
        self.sent.append(content)


class DummyResponse:
    def __init__(self):
        self.deferred = False

    async def defer(self):
        self.deferred = True


class DummyInteraction:
    def __init__(self):
        self.channel_id = 123
        class User:
            display_name = "Tester"
        self.user = User()
        self.response = DummyResponse()
        self.followup = DummyFollowup()


@pytest.mark.asyncio
async def test_review_splits_long_message(monkeypatch):
    bot = type("B", (), {})()
    # simulate ask_ai returning a long string
    long_text = "x" * 5000
    async def fake_ask_ai(channel_id, user_name, user_message, system_prompt=None, message_type=None):
        return long_text, "provider"

    bot.ask_ai = fake_ask_ai
    cog = CodeReview(bot)
    interaction = DummyInteraction()

    # `cog.review` is an `app_commands.Command`, so call its callback directly
    await cog.review.callback(cog, interaction, code="print('hi')", language="python")

    # after running, followup.sent should contain the long text split into multiple parts
    assert len(interaction.followup.sent) >= 3
    assert ''.join(interaction.followup.sent) == long_text
    # deferred should be True
    assert interaction.response.deferred
