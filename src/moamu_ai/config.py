from pathlib import Path
from typing import Literal, Optional

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from moamu_ai.prompts import DEFAULT_PROMPT_VERSION, get_prompt_definition


class Settings(BaseSettings):
    """환경 변수와 `.env`에서 AI 서버 설정을 읽는다."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    ai_provider: Literal["gemini", "ollama"] = "gemini"
    ai_image_source: Literal["s3", "local"] = "s3"
    ai_model_version: str = Field(default="photo-verifier-v1", min_length=1, max_length=50)
    ai_image_root: Path = Path("./data/images")
    ai_prompt_version: str = DEFAULT_PROMPT_VERSION
    gemini_token_api_key: Optional[SecretStr] = None
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_thinking_level: Optional[Literal["minimal", "low", "medium", "high"]] = None
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3-vl:2b"
    s3_access_key_id: Optional[SecretStr] = None
    s3_secret_access_key: Optional[SecretStr] = None
    aws_region: str = "ap-northeast-2"
    s3_bucket: Optional[str] = None
    ai_provider_timeout_seconds: float = Field(default=45.0, gt=0, le=300)
    gemini_max_live_calls_per_run: int = Field(default=6, ge=1, le=6)

    @field_validator("ai_prompt_version")
    @classmethod
    def validate_prompt_version(cls, value: str) -> str:
        """설정된 프롬프트 버전이 등록되어 있는지 확인한다."""
        get_prompt_definition(value)
        return value
