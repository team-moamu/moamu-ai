import mimetypes
from pathlib import Path
from time import perf_counter
from typing import Optional

from google import genai
from google.genai import types
from pydantic import SecretStr, ValidationError

from moamu_ai.errors import (
    InvalidModelOutputError,
    ModelProviderError,
    ProviderConfigurationError,
)
from moamu_ai.prompts import build_verification_prompt
from moamu_ai.providers.base import InferenceResult, InferenceUsage
from moamu_ai.schemas import ConditionSnapshot, PhotoVerificationResponse


class GeminiPhotoJudge:
    def __init__(
        self,
        api_key: Optional[SecretStr],
        model: str,
        timeout_seconds: float = 45.0,
        client=None,
    ):
        if api_key is None or not api_key.get_secret_value():
            raise ProviderConfigurationError("GEMINI_TOKEN_API_KEY is not configured")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.client = client or genai.Client(
            api_key=api_key.get_secret_value(),
            http_options=types.HttpOptions(
                timeout=int(timeout_seconds * 1000),
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )

    def evaluate(self, image_path: Path, conditions: list[ConditionSnapshot]) -> InferenceResult:
        try:
            image_bytes = image_path.read_bytes()
        except OSError as exc:
            raise ModelProviderError("validated image could not be read") from exc
        mime_type, _ = mimetypes.guess_type(image_path.name)
        if not mime_type or not mime_type.startswith("image/"):
            mime_type = "image/jpeg"
        image = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        prompt = build_verification_prompt(conditions)
        started = perf_counter()
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[prompt, image],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=_gemini_response_schema(),
                    temperature=0,
                    max_output_tokens=256,
                ),
            )
        except Exception as exc:
            raise ModelProviderError("Gemini request failed") from exc

        latency_ms = (perf_counter() - started) * 1000
        response_text = getattr(response, "text", None)
        if not response_text:
            raise InvalidModelOutputError("Gemini returned no structured result")
        try:
            parsed = PhotoVerificationResponse.model_validate_json(response_text)
        except (ValidationError, ValueError) as exc:
            raise InvalidModelOutputError("Gemini returned an invalid result") from exc

        metadata = getattr(response, "usage_metadata", None)
        prompt_tokens = getattr(metadata, "prompt_token_count", None)
        output_tokens = getattr(metadata, "candidates_token_count", None)
        total_tokens = getattr(metadata, "total_token_count", None)
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


def _gemini_response_schema() -> dict:
    """Build Gemini's supported schema subset from the stricter API models."""
    schema = PhotoVerificationResponse.model_json_schema()
    pending = [schema]
    while pending:
        current = pending.pop()
        if isinstance(current, dict):
            current.pop("additionalProperties", None)
            pending.extend(current.values())
        elif isinstance(current, list):
            pending.extend(current)
    return schema
