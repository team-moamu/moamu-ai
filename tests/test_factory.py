import pytest
from pydantic import SecretStr

from moamu_ai.config import Settings
from moamu_ai.providers import factory


class CapturingJudge:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


@pytest.mark.parametrize("provider", ["gemini", "ollama"])
def test_provider_factory_passes_the_configured_prompt_version(monkeypatch, provider):
    monkeypatch.setattr(factory, "GeminiPhotoJudge", CapturingJudge)
    monkeypatch.setattr(factory, "OllamaPhotoJudge", CapturingJudge)
    settings = Settings(
        _env_file=None,
        ai_provider=provider,
        gemini_token_api_key=SecretStr("test-key"),
        ai_prompt_version="photo-verification-v3",
        gemini_thinking_level="low",
    )

    judge = factory.create_photo_judge(settings)

    assert judge.kwargs["prompt_version"] == "photo-verification-v3"
    if provider == "gemini":
        assert judge.kwargs["thinking_level"] == "low"
