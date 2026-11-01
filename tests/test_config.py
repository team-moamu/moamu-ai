from pydantic import SecretStr

from moamu_ai.config import Settings


def test_settings_reads_the_user_named_gemini_environment_variable(monkeypatch):
    monkeypatch.setenv("GEMINI_TOKEN_API_KEY", "test-secret")

    settings = Settings(_env_file=None)

    assert isinstance(settings.gemini_token_api_key, SecretStr)
    assert settings.gemini_token_api_key.get_secret_value() == "test-secret"


def test_settings_default_to_low_cost_gemini_candidate_and_local_ollama(monkeypatch):
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)

    settings = Settings(_env_file=None)

    assert settings.gemini_model == "gemini-3.5-flash-lite"
    assert settings.ollama_model == "qwen3-vl:2b"
