from pathlib import Path
from types import SimpleNamespace

from google.genai._transformers import t_schema
from pydantic import SecretStr

from moamu_ai.providers.gemini import GeminiPhotoJudge, _gemini_response_schema
from moamu_ai.schemas import (
    ConditionSnapshot,
    ConditionStatus,
)


class FakeGeminiModels:
    """Gemini 요청 인자와 가짜 응답을 기록하는 테스트 대역."""

    def __init__(self, response):
        """가짜 Gemini 응답과 요청 기록 공간을 초기화한다."""
        self.response = response
        self.kwargs = None

    def generate_content(self, **kwargs):
        """호출 인자를 저장하고 설정된 응답을 반환한다."""
        self.kwargs = kwargs
        return self.response


def test_gemini_sends_image_and_structured_output_config(tmp_path: Path):
    """이미지와 구조화 응답 설정이 Gemini에 전달되는지 확인한다."""
    image_path = tmp_path / "photo.jpg"
    image_path.write_bytes(b"fake image bytes")
    response = SimpleNamespace(
        text=(
            '{"results":[{"challenge_condition_id":1,"status":"MET",'
            '"reason":"A bottle is visible."},{"challenge_condition_id":2,'
            '"status":"NOT_MET","reason":"No drinking action is visible."}]}'
        ),
        usage_metadata=SimpleNamespace(
            prompt_token_count=20,
            candidates_token_count=4,
            total_token_count=31,
            thoughts_token_count=7,
        ),
    )
    models = FakeGeminiModels(response)
    judge = GeminiPhotoJudge(
        api_key=SecretStr("test-key"),
        model="gemini-3.5-flash-lite",
        prompt_version="photo-verification-v3",
        thinking_level="low",
        client=SimpleNamespace(models=models),
    )
    conditions = [
        ConditionSnapshot(
            challenge_condition_id=1,
            code="WATER_BOTTLE",
            condition_type="OBJECT_PRESENT",
            description="A water bottle is visible",
            required=True,
            sort_order=1,
        ),
        ConditionSnapshot(
            challenge_condition_id=2,
            code="DRINKING",
            condition_type="ACTIVITY_IN_PROGRESS",
            description="The person is drinking",
            required=True,
            sort_order=2,
        ),
    ]

    result = judge.evaluate(image_path, conditions)

    assert result.results[0].status == ConditionStatus.MET
    assert result.usage.model == "gemini-3.5-flash-lite"
    assert result.usage.prompt_tokens == 20
    assert result.usage.thinking_tokens == 7
    assert models.kwargs["model"] == "gemini-3.5-flash-lite"
    assert "related or similar item as a match" in models.kwargs["contents"][0]
    assert "gummy candy is not a tablet or capsule" not in models.kwargs["contents"][0]
    assert models.kwargs["contents"][1].inline_data.data == b"fake image bytes"
    assert models.kwargs["config"].response_mime_type == "application/json"
    assert models.kwargs["config"].temperature == 0
    assert models.kwargs["config"].max_output_tokens == 512
    assert models.kwargs["config"].thinking_config.thinking_level.value.lower() == "low"


def test_gemini_provider_requires_the_exact_configured_api_key_name():
    """Gemini 공급자가 요구하는 API 키 설정명을 확인한다."""
    from moamu_ai.errors import ProviderConfigurationError

    try:
        GeminiPhotoJudge(api_key=None, model="gemini-3.5-flash-lite")
    except ProviderConfigurationError as error:
        assert "GEMINI_TOKEN_API_KEY" in str(error)
    else:
        raise AssertionError("missing key should prevent a live provider")


def test_gemini_structured_response_schema_is_supported_by_the_sdk():
    """응답 스키마가 Gemini SDK에서 허용되는 형식인지 확인한다."""
    schema = _gemini_response_schema()
    gemini_schema = t_schema(None, schema)

    assert gemini_schema.additional_properties is None
    assert gemini_schema.properties["results"].items.additional_properties is None
