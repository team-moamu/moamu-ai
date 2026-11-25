import base64
import binascii
import mimetypes
from pathlib import Path
from time import perf_counter
from typing import Optional

from google import genai
from google.genai import types
from pydantic import SecretStr

from moamu_ai.artwork_prompts import (
    DEFAULT_ARTWORK_PROMPT_VERSION,
    build_artwork_edit_prompt,
    get_artwork_prompt_definition,
)
from moamu_ai.errors import (
    InvalidModelOutputError,
    ModelProviderError,
    ProviderConfigurationError,
)
from moamu_ai.providers.base import ArtworkEditResult
from moamu_ai.schemas import ArtworkGenerationRequest


class GeminiArtworkEditor:
    """Gemini 이미지 편집 모델로 원본 명화를 목표에 맞게 편집한다."""

    def __init__(
        self,
        api_key: Optional[SecretStr],
        model: str,
        timeout_seconds: float = 90.0,
        client=None,
        prompt_version: str = DEFAULT_ARTWORK_PROMPT_VERSION,
    ):
        """Gemini 이미지 편집 클라이언트와 모델 설정을 초기화한다."""
        if api_key is None or not api_key.get_secret_value():
            raise ProviderConfigurationError("GEMINI_TOKEN_API_KEY is not configured")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.prompt_version = get_artwork_prompt_definition(prompt_version).version
        self.client = client or genai.Client(
            api_key=api_key.get_secret_value(),
            http_options=types.HttpOptions(
                timeout=int(timeout_seconds * 1000),
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )

    def edit(
        self,
        image_path: Path,
        request: ArtworkGenerationRequest,
    ) -> ArtworkEditResult:
        """원본 이미지와 목표 정보를 Gemini에 전달하고 편집 이미지를 반환한다."""
        try:
            image_bytes = image_path.read_bytes()
        except OSError as exc:
            raise ModelProviderError("source artwork could not be read") from exc
        if not image_bytes:
            raise ModelProviderError("source artwork is empty")

        source_mime_type, _ = mimetypes.guess_type(image_path.name)
        if not source_mime_type or not source_mime_type.startswith("image/"):
            raise ModelProviderError("source artwork has an unsupported file extension")

        prompt = build_artwork_edit_prompt(request, version=self.prompt_version)
        try:
            started = perf_counter()
            interaction = self.client.interactions.create(
                model=self.model,
                input=[
                    {"type": "text", "text": prompt},
                    {
                        "type": "image",
                        "data": base64.b64encode(image_bytes).decode("ascii"),
                        "mime_type": source_mime_type,
                    },
                ],
                response_format={
                    "type": "image",
                    "mime_type": "image/jpeg",
                    "image_size": "1K",
                },
            )
            latency_ms = (perf_counter() - started) * 1000
        except Exception as exc:
            raise ModelProviderError("Gemini artwork edit failed") from exc

        output_image = getattr(interaction, "output_image", None)
        if output_image is None:
            raise InvalidModelOutputError("Gemini returned no artwork image")
        image_data = getattr(output_image, "data", None)
        mime_type = getattr(output_image, "mime_type", None)
        decoded_image, detected_mime_type = _decode_image(image_data)
        if mime_type is not None and mime_type != detected_mime_type:
            raise InvalidModelOutputError("Gemini artwork MIME type does not match image bytes")

        return ArtworkEditResult(
            image_bytes=decoded_image,
            content_type=detected_mime_type,
            model=self.model,
            latency_ms=latency_ms,
        )


def _decode_image(image_data) -> tuple[bytes, str]:
    """Gemini 응답의 Base64 데이터를 이미지 바이트로 검증한다."""
    if isinstance(image_data, bytes):
        image_bytes = image_data
    elif isinstance(image_data, str):
        try:
            image_bytes = base64.b64decode(image_data, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise InvalidModelOutputError("Gemini returned invalid Base64 artwork") from exc
    else:
        raise InvalidModelOutputError("Gemini returned no artwork data")

    mime_type = _detect_image_mime_type(image_bytes)
    if mime_type is None:
        raise InvalidModelOutputError("Gemini returned an unsupported artwork format")
    return image_bytes, mime_type


def _detect_image_mime_type(image_bytes: bytes) -> Optional[str]:
    """지원하는 이미지 서명으로 응답의 실제 MIME 타입을 확인한다."""
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    return None
