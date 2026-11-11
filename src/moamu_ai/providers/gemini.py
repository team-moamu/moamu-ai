import mimetypes
from pathlib import Path
from time import perf_counter
from typing import Literal, Optional

from google import genai
from google.genai import types
from pydantic import SecretStr, ValidationError

from moamu_ai.errors import (
    InvalidModelOutputError,
    ModelProviderError,
    ProviderConfigurationError,
)
from moamu_ai.prompts import (
    DEFAULT_PROMPT_VERSION,
    build_verification_prompt,
    get_prompt_definition,
)
from moamu_ai.providers.base import InferenceResult, InferenceUsage
from moamu_ai.schemas import ConditionSnapshot, ModelJudgmentResponse

GEMINI_MAX_OUTPUT_TOKENS = 512


class GeminiPhotoJudge:
    """Gemini API로 이미지별 인증 조건을 판정한다."""

    def __init__(
        self,
        api_key: Optional[SecretStr],
        model: str,
        timeout_seconds: float = 45.0,
        client=None,
        prompt_version: str = DEFAULT_PROMPT_VERSION,
        thinking_level: Optional[Literal["minimal", "low", "medium", "high"]] = None,
    ):
        """Gemini 클라이언트와 판정 옵션을 설정한다.

        Args:
            api_key: Gemini API 인증 키.
            model: 사용할 Gemini 모델 이름.
            timeout_seconds: 요청 제한 시간(초).
            client: 테스트 등에 사용할 대체 클라이언트.
            prompt_version: 적용할 프롬프트 버전.
            thinking_level: Gemini 추론 단계 설정.

        Raises:
            ProviderConfigurationError: API 키가 비어 있는 경우.
        """
        if api_key is None or not api_key.get_secret_value():
            raise ProviderConfigurationError("GEMINI_TOKEN_API_KEY is not configured")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.prompt_version = get_prompt_definition(prompt_version).version
        self.thinking_level = thinking_level
        self.max_output_tokens = GEMINI_MAX_OUTPUT_TOKENS
        self.client = client or genai.Client(
            api_key=api_key.get_secret_value(),
            http_options=types.HttpOptions(
                timeout=int(timeout_seconds * 1000),
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )

    def evaluate(self, image_path: Path, conditions: list[ConditionSnapshot]) -> InferenceResult:
        """Gemini에 이미지와 조건을 보내 판정 및 토큰 사용량을 반환한다.

        Args:
            image_path: 모델에 전달할 이미지 파일 경로.
            conditions: 판정할 인증 조건 목록.

        Returns:
            조건별 판정 결과와 Gemini 사용량 정보.

        Raises:
            ModelProviderError: 이미지 읽기 또는 API 호출에 실패한 경우.
            InvalidModelOutputError: Gemini 응답이 없거나 형식이 잘못된 경우.
        """
        try:
            image_bytes = image_path.read_bytes()
        except OSError as exc:
            raise ModelProviderError("validated image could not be read") from exc
        mime_type, _ = mimetypes.guess_type(image_path.name)
        if not mime_type or not mime_type.startswith("image/"):
            mime_type = "image/jpeg"
        image = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        prompt = build_verification_prompt(conditions, version=self.prompt_version)
        config = {
            "response_mime_type": "application/json",
            "response_schema": _gemini_response_schema(),
            "temperature": 0,
            "max_output_tokens": self.max_output_tokens,
        }
        if self.thinking_level is not None:
            config["thinking_config"] = types.ThinkingConfig(
                thinking_level=self.thinking_level
            )
        started = perf_counter()
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[prompt, image],
                config=types.GenerateContentConfig(**config),
            )
        except Exception as exc:
            raise ModelProviderError("Gemini request failed") from exc

        latency_ms = (perf_counter() - started) * 1000
        response_text = getattr(response, "text", None)
        if not response_text:
            raise InvalidModelOutputError("Gemini returned no structured result")
        try:
            parsed = ModelJudgmentResponse.model_validate_json(response_text)
        except (ValidationError, ValueError) as exc:
            raise InvalidModelOutputError("Gemini returned an invalid result") from exc

        metadata = getattr(response, "usage_metadata", None)
        prompt_tokens = getattr(metadata, "prompt_token_count", None)
        output_tokens = getattr(metadata, "candidates_token_count", None)
        total_tokens = getattr(metadata, "total_token_count", None)
        thinking_tokens = getattr(metadata, "thoughts_token_count", None)
        return InferenceResult(
            results=parsed.results,
            usage=InferenceUsage(
                model=self.model,
                latency_ms=latency_ms,
                prompt_tokens=prompt_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                thinking_tokens=thinking_tokens,
            ),
        )


def _gemini_response_schema() -> dict:
    """Pydantic 응답 모델을 Gemini가 지원하는 스키마로 변환한다."""
    schema = ModelJudgmentResponse.model_json_schema()
    pending = [schema]
    while pending:
        current = pending.pop()
        if isinstance(current, dict):
            current.pop("additionalProperties", None)
            pending.extend(current.values())
        elif isinstance(current, list):
            pending.extend(current)
    return schema
