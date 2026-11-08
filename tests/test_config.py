from pydantic import SecretStr

from moamu_ai.config import Settings


def test_settings_reads_the_user_named_gemini_environment_variable(monkeypatch):
    """설정이 지정된 Gemini 키 환경 변수명을 읽는지 확인한다."""
    monkeypatch.setenv("GEMINI_TOKEN_API_KEY", "test-secret")

    settings = Settings(_env_file=None)

    assert isinstance(settings.gemini_token_api_key, SecretStr)
    assert settings.gemini_token_api_key.get_secret_value() == "test-secret"


def test_settings_default_to_low_cost_gemini_candidate_and_local_ollama(monkeypatch):
    """기본 Gemini 후보와 로컬 Ollama 설정을 확인한다."""
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)

    settings = Settings(_env_file=None)

    assert settings.gemini_model == "gemini-3.5-flash-lite"
    assert settings.ollama_model == "qwen3-vl:2b"


def test_settings_selects_a_prompt_version_from_the_environment(monkeypatch):
    """환경 변수로 프롬프트 버전을 선택하는지 확인한다."""
    monkeypatch.setenv("AI_PROMPT_VERSION", "photo-verification-v3")

    settings = Settings(_env_file=None)

    assert settings.ai_prompt_version == "photo-verification-v3"


def test_settings_selects_gemini_thinking_level_from_the_environment(monkeypatch):
    """환경 변수로 Gemini 추론 단계를 선택하는지 확인한다."""
    monkeypatch.setenv("GEMINI_THINKING_LEVEL", "low")

    settings = Settings(_env_file=None)

    assert settings.gemini_thinking_level == "low"


def test_settings_rejects_an_unknown_prompt_version(monkeypatch):
    """등록되지 않은 프롬프트 버전을 거부하는지 확인한다."""
    import pytest
    from pydantic import ValidationError

    monkeypatch.setenv("AI_PROMPT_VERSION", "photo-verification-v99")

    with pytest.raises(ValidationError, match="Unsupported prompt version"):
        Settings(_env_file=None)
