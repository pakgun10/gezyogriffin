"""Vision payload tests for Telegram's OpenAI-compatible provider path."""

import asyncio

from opengriffin import bot, providers


def test_stream_selected_provider_sends_openai_multimodal_content(monkeypatch):
    seen = []

    class FakeProvider:
        model = "test-model"

        async def chat(self, messages, tools=None):
            seen.append(messages)
            return {
                "content": "gambar terlihat",
                "tool_calls": [],
                "input_tokens": 3,
                "output_tokens": 2,
            }

    monkeypatch.setattr(bot.aliases_module, "get_chat_model", lambda _chat_id: {})
    monkeypatch.setattr(providers, "get_provider", lambda _name: FakeProvider())
    image = "data:image/jpeg;base64,ZmFrZQ=="
    result = asyncio.run(bot._stream_selected_provider(1, "Apa ini?", "cx/test", image))

    assert result[0] == "gambar terlihat"
    user = seen[0][1]
    assert user["role"] == "user"
    assert user["content"][0] == {"type": "text", "text": "Apa ini?"}
    assert user["content"][1] == {"type": "image_url", "image_url": {"url": image}}


def test_photo_data_url_uses_largest_photo_and_rejects_oversize(monkeypatch):
    class FakeFile:
        async def download_as_bytearray(self):
            return bytearray(b"jpeg")

    class FakePhoto:
        def __init__(self, size):
            self.size = size

        async def get_file(self):
            return FakeFile()

    message = type("Message", (), {"photo": [FakePhoto(1), FakePhoto(2)]})()
    value = asyncio.run(bot._photo_data_url(message))
    assert value == "data:image/jpeg;base64,anBlZw=="

    monkeypatch.setattr(bot, "TELEGRAM_IMAGE_MAX_BYTES", 2)
    try:
        asyncio.run(bot._photo_data_url(message))
    except ValueError as exc:
        assert "gambar terlalu besar" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("oversize photo was accepted")
