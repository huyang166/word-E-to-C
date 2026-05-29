import pytest

from app.ai_client import AIClient, MissingApiKeyError, build_sync_prompt
from app.config import Settings


def test_settings_default_openai_base_url():
    settings = Settings(openai_api_key="test-key", openai_model="test-model")

    assert settings.openai_base_url == "https://api.openai.com/v1"


def test_settings_requires_api_key_for_ai_calls():
    settings = Settings(openai_api_key="", openai_model="test-model")

    assert not settings.has_openai_key


def test_builds_english_to_chinese_prompt():
    messages = build_sync_prompt(
        direction="en_to_zh",
        source_text="The revised English paragraph.",
        target_text="原中文段落。",
    )

    assert messages[0]["role"] == "system"
    assert "只返回建议段落文本" in messages[0]["content"]
    assert "英文修改后段落" in messages[1]["content"]
    assert "当前中文对应段落" in messages[1]["content"]


@pytest.mark.asyncio
async def test_missing_api_key_raises_clear_error():
    client = AIClient(Settings(openai_api_key="", openai_model="test-model"))

    with pytest.raises(MissingApiKeyError):
        await client.suggest(
            direction="en_to_zh",
            source_text="A",
            target_text="甲",
        )
