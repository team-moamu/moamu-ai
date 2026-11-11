import pytest
from pydantic import SecretStr

from moamu_ai.config import Settings
from moamu_ai.providers import factory


class CapturingJudge:
    """판정기 생성 옵션을 확인하기 위한 테스트 대역."""

    def __init__(self, **kwargs):
        """생성 시 전달된 옵션을 보관한다."""
        self.kwargs = kwargs


@pytest.mark.parametrize("provider", ["gemini", "ollama"])
def test_provider_factory_passes_the_configured_prompt_version(monkeypatch, provider):
    """공급자 생성기가 설정된 프롬프트 버전을 전달하는지 확인한다."""
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
