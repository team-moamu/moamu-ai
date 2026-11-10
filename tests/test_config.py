import pytest
from pydantic import SecretStr

from moamu_ai.config import Settings


def test_settings_reads_the_user_named_gemini_environment_variable(monkeypatch):
    """설정이 지정된 Gemini 키 환경 변수명을 읽는지 확인한다."""
    monkeypatch.setenv("GEMINI_TOKEN_API_KEY", "test-secret")

    settings = Settings(_env_file=None)

    assert isinstance(settings.gemini_token_api_key, SecretStr)
    assert settings.gemini_token_api_key.get_secret_value() == "test-secret"


@pytest.mark.parametrize(
    ("access_key_name", "secret_key_name", "session_token_name"),
    [
        ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"),
        ("S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY", "S3_SESSION_TOKEN"),
    ],
)
def test_settings_reads_aws_and_legacy_s3_credentials(
    monkeypatch, access_key_name, secret_key_name, session_token_name
):
    """AWS 표준 이름과 기존 S3 이름에서 자격 증명을 읽는다."""
    credential_names = (
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "S3_ACCESS_KEY_ID",
        "S3_SECRET_ACCESS_KEY",
        "S3_SESSION_TOKEN",
    )
    for name in credential_names:
        monkeypatch.delenv(name, raising=False)

    monkeypatch.setenv(access_key_name, "test-access-key")
    monkeypatch.setenv(secret_key_name, "test-secret-key")
    monkeypatch.setenv(session_token_name, "test-session-token")

    settings = Settings(_env_file=None)

    assert isinstance(settings.s3_access_key_id, SecretStr)
    assert isinstance(settings.s3_secret_access_key, SecretStr)
    assert isinstance(settings.s3_session_token, SecretStr)
    assert settings.s3_access_key_id.get_secret_value() == "test-access-key"
    assert settings.s3_secret_access_key.get_secret_value() == "test-secret-key"
    assert settings.s3_session_token.get_secret_value() == "test-session-token"


def test_settings_reads_aws_credentials_from_dotenv_file(tmp_path, monkeypatch):
    """실제 프로세스 환경이 아닌 dotenv 파일의 AWS 표준 이름을 읽는다."""
    for name in (
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "S3_ACCESS_KEY_ID",
        "S3_SECRET_ACCESS_KEY",
        "S3_SESSION_TOKEN",
    ):
        monkeypatch.delenv(name, raising=False)

    env_file = tmp_path / ".env"
    env_file.write_text(
        "AWS_ACCESS_KEY_ID=dotenv-access-key\n"
        "AWS_SECRET_ACCESS_KEY=dotenv-secret-key\n"
        "AWS_SESSION_TOKEN=dotenv-session-token\n",
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.s3_access_key_id.get_secret_value() == "dotenv-access-key"
    assert settings.s3_secret_access_key.get_secret_value() == "dotenv-secret-key"
    assert settings.s3_session_token.get_secret_value() == "dotenv-session-token"


def test_process_environment_overrides_dotenv_credentials(tmp_path, monkeypatch):
    """프로세스 환경변수가 dotenv의 같은 AWS 키보다 우선한다."""
    for name in (
        "S3_ACCESS_KEY_ID",
        "S3_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "S3_SESSION_TOKEN",
    ):
        monkeypatch.delenv(name, raising=False)

    env_file = tmp_path / ".env"
    env_file.write_text(
        "AWS_ACCESS_KEY_ID=dotenv-access-key\n"
        "AWS_SECRET_ACCESS_KEY=dotenv-secret-key\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "process-access-key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "process-secret-key")

    settings = Settings(_env_file=env_file)

    assert settings.s3_access_key_id.get_secret_value() == "process-access-key"
    assert settings.s3_secret_access_key.get_secret_value() == "process-secret-key"


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
