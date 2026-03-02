import providers
import config

# Basic fake provider to simulate token usage reporting
class DummyUsage:
    def __init__(self, text="hello", inp=1, out=2):
        class Choice:
            def __init__(self, content):
                self.message = type("M", (), {"content": content})()
        self.choices = [Choice(text)]
        self.usage = {"prompt_tokens": inp, "completion_tokens": out, "total_tokens": inp + out}

class DummyClient:
    def __init__(self, *args, **kwargs):
        pass

    class chat:
        class completions:
            @staticmethod
            def create(*args, **kwargs):
                # ignore arguments and return a fixed usage object
                return DummyUsage()


def test_chat_returns_tokens(monkeypatch):
    # register a fake provider in the clients map
    providers._clients["testprov"] = DummyClient()
    # ensure config entry has a price so we can verify cost calculation separately
    config.PROVIDERS["testprov"] = {
        "name": "Test Provider",
        "model": "fake-model",
        "api_key": "",
        "free": False,
        "price_per_1k_tokens": 2.5,
    }

    text, name, inp, out, total = providers.chat([], "sys", primary_provider="testprov")
    assert name == "testprov"
    assert text == "hello"
    assert inp == 1
    assert out == 2
    assert total == 3

    # cost computation is performed by caller, so we check that using the returned values
    estimated = (total / 1000) * config.PROVIDERS["testprov"]["price_per_1k_tokens"]
    assert estimated == 0.0075
