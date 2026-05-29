from app.config import Settings


def test_settings_default_openai_base_url():
    settings = Settings(openai_api_key="test-key", openai_model="test-model")

    assert settings.openai_base_url == "https://api.openai.com/v1"


def test_settings_requires_api_key_for_ai_calls():
    settings = Settings(openai_api_key="", openai_model="test-model")

    assert not settings.has_openai_key
