import base64
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from moamu_ai.errors import (
    InvalidModelOutputError,
    ModelProviderError,
    ProviderConfigurationError,
)
from moamu_ai.providers.gemini_artwork import GeminiArtworkEditor
from moamu_ai.schemas import ArtworkGenerationRequest


class FakeInteractions:
    """Gemini 편집 요청을 기록하고 미리 정한 응답을 반환한다."""

    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.response


class FakeClient:
    """Gemini 이미지 편집 API 대역."""

    def __init__(self, interactions):
        self.interactions = interactions


def request():
    return ArtworkGenerationRequest.model_validate(
        {
            "taskId": 91,
            "taskVersion": 1,
            "expiresAt": "2026-11-23T04:02:00Z",
            "normalizedGoal": "영어 표현을 노트에 기록하기",
            "categoryPath": {"major": "학습", "middle": "어학", "minor": "영어"},
            "conditions": ["영어 표현이 필기된 노트가 보여야 한다"],
            "photoGuide": "노트의 영어 필기가 읽히도록 촬영",
        }
    )


def png_bytes():
    return b"\x89PNG\r\n\x1a\nmoamu-image-bytes"


def jpeg_bytes():
    return b"\xff\xd8\xffmoamu-image-bytes"


def test_gemini_editor_sends_reference_image_and_challenge_context(tmp_path: Path):
    source_path = tmp_path / "source.png"
    source_path.write_bytes(png_bytes())
    response = SimpleNamespace(
        output_image=SimpleNamespace(
            data=base64.b64encode(jpeg_bytes()).decode("ascii"),
            mime_type="image/jpeg",
        )
    )
    interactions = FakeInteractions(response=response)
    editor = GeminiArtworkEditor(
        api_key=SecretStr("test-key"),
        model="gemini-test-image",
        client=FakeClient(interactions),
    )

    result = editor.edit(source_path, request())

    call = interactions.calls[0]
    assert call["model"] == "gemini-test-image"
    assert call["response_format"] == {
        "type": "image",
        "mime_type": "image/jpeg",
        "image_size": "1K",
    }
    assert "영어 표현을 노트에 기록하기" in call["input"][0]["text"]
    assert call["input"][1] == {
        "type": "image",
        "data": base64.b64encode(png_bytes()).decode("ascii"),
        "mime_type": "image/png",
    }
    assert result.image_bytes == jpeg_bytes()
    assert result.content_type == "image/jpeg"


def test_gemini_editor_rejects_missing_api_key():
    with pytest.raises(ProviderConfigurationError, match="GEMINI_TOKEN_API_KEY"):
        GeminiArtworkEditor(api_key=None, model="gemini-test-image")


def test_gemini_editor_wraps_model_call_errors(tmp_path: Path):
    source_path = tmp_path / "source.png"
    source_path.write_bytes(png_bytes())
    interactions = FakeInteractions(error=RuntimeError("provider error"))
    editor = GeminiArtworkEditor(
        api_key=SecretStr("test-key"),
        model="gemini-test-image",
        client=FakeClient(interactions),
    )

    with pytest.raises(ModelProviderError, match="Gemini artwork edit failed"):
        editor.edit(source_path, request())


@pytest.mark.parametrize(
    "response",
    [
        None,
        SimpleNamespace(output_image=None),
        SimpleNamespace(
            output_image=SimpleNamespace(data="not-base64", mime_type="image/png")
        ),
        SimpleNamespace(
            output_image=SimpleNamespace(
                data=base64.b64encode(b"not-an-image").decode("ascii"),
                mime_type="image/png",
            )
        ),
    ],
)
def test_gemini_editor_rejects_missing_or_invalid_image_output(tmp_path: Path, response):
    source_path = tmp_path / "source.png"
    source_path.write_bytes(png_bytes())
    editor = GeminiArtworkEditor(
        api_key=SecretStr("test-key"),
        model="gemini-test-image",
        client=FakeClient(FakeInteractions(response=response)),
    )

    with pytest.raises(InvalidModelOutputError):
        editor.edit(source_path, request())


def test_gemini_editor_rejects_unreadable_source_image(tmp_path: Path):
    editor = GeminiArtworkEditor(
        api_key=SecretStr("test-key"),
        model="gemini-test-image",
        client=FakeClient(FakeInteractions()),
    )

    with pytest.raises(ModelProviderError, match="source artwork could not be read"):
        editor.edit(tmp_path / "missing.png", request())
