import base64
from pathlib import Path
from time import perf_counter
from typing import Optional

import httpx
from pydantic import ValidationError

from moamu_ai.errors import InvalidModelOutputError, ModelProviderError
from moamu_ai.prompts import (
    DEFAULT_PROMPT_VERSION,
    build_verification_prompt,
    get_prompt_definition,
)
from moamu_ai.providers.base import InferenceResult, InferenceUsage
from moamu_ai.schemas import ConditionSnapshot, ModelJudgmentResponse


class OllamaPhotoJudge:
    """로컬 Ollama 서버로 이미지별 인증 조건을 판정한다."""

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: float = 45.0,
        client: Optional[httpx.Client] = None,
        prompt_version: str = DEFAULT_PROMPT_VERSION,
    ):
        """Ollama 서버 주소, 모델, 요청 옵션을 설정한다."""
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.prompt_version = get_prompt_definition(prompt_version).version
        self.client = client or httpx.Client(timeout=timeout_seconds)

    def evaluate(self, image_path: Path, conditions: list[ConditionSnapshot]) -> InferenceResult:
        """Ollama에 이미지와 조건을 보내 판정 결과를 반환한다.

        Args:
            image_path: 모델에 전달할 이미지 파일 경로.
            conditions: 판정할 인증 조건 목록.

        Returns:
            조건별 판정 결과와 추론 사용량 정보.

        Raises:
            ModelProviderError: 이미지 읽기 또는 Ollama 요청에 실패한 경우.
            InvalidModelOutputError: Ollama 응답이 없거나 형식이 잘못된 경우.
        """
        try:
            image_bytes = image_path.read_bytes()
        except OSError as exc:
            raise ModelProviderError("validated image could not be read") from exc
        encoded_image = base64.b64encode(image_bytes).decode("ascii")
        prompt = build_verification_prompt(conditions, version=self.prompt_version)
        schema = ModelJudgmentResponse.model_json_schema()
        started = perf_counter()
        try:
            response = self.client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt,
                            "images": [encoded_image],
                        }
                    ],
                    "format": schema,
                    "options": {"temperature": 0},
                    "stream": False,
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ModelProviderError("Ollama request failed") from exc

        latency_ms = (perf_counter() - started) * 1000
        response_text = payload.get("message", {}).get("content")
        if not isinstance(response_text, str) or not response_text:
            raise InvalidModelOutputError("Ollama returned no structured result")
        try:
            parsed = ModelJudgmentResponse.model_validate_json(response_text)
        except (ValidationError, ValueError) as exc:
            raise InvalidModelOutputError("Ollama returned an invalid result") from exc

        prompt_tokens = payload.get("prompt_eval_count")
        output_tokens = payload.get("eval_count")
        total_tokens = None
        if isinstance(prompt_tokens, int) and isinstance(output_tokens, int):
            total_tokens = prompt_tokens + output_tokens
        return InferenceResult(
            results=parsed.results,
            usage=InferenceUsage(
                model=self.model,
                latency_ms=latency_ms,
                prompt_tokens=prompt_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
            ),
        )
