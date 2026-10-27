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
    def __init__(self, response):
        self.response = response
        self.kwargs = None

    def generate_content(self, **kwargs):
        self.kwargs = kwargs
        return self.response


def test_gemini_sends_image_and_structured_output_config(tmp_path: Path):
    image_path = tmp_path / "photo.jpg"
    image_path.write_bytes(b"fake image bytes")
    response = SimpleNamespace(
        text=(
            '{"results":[{"challenge_condition_id":1,"status":"MET"},'
            '{"challenge_condition_id":2,"status":"NOT_MET"}]}'
        ),
        usage_metadata=SimpleNamespace(
            prompt_token_count=20,
            candidates_token_count=4,
            total_token_count=24,
        ),
    )
    models = FakeGeminiModels(response)
    judge = GeminiPhotoJudge(
        api_key=SecretStr("test-key"),
        model="gemini-3.5-flash-lite",
        client=SimpleNamespace(models=models),
    )
    conditions = [
        ConditionSnapshot(
            challenge_condition_id=1,
            code="WATER_BOTTLE",
            condition_type="OBJECT_VISIBLE",
            description="A water bottle is visible",
            required=True,
            sort_order=1,
        ),
        ConditionSnapshot(
            challenge_condition_id=2,
            code="DRINKING",
            condition_type="ACTION_VISIBLE",
            description="The person is drinking",
            required=True,
            sort_order=2,
        ),
    ]

    result = judge.evaluate(image_path, conditions)

    assert result.results[0].status == ConditionStatus.MET
    assert result.usage.model == "gemini-3.5-flash-lite"
    assert result.usage.prompt_tokens == 20
    assert models.kwargs["model"] == "gemini-3.5-flash-lite"
    assert models.kwargs["contents"][1].inline_data.data == b"fake image bytes"
    assert models.kwargs["config"].response_mime_type == "application/json"
    assert models.kwargs["config"].temperature == 0


def test_gemini_provider_requires_the_exact_configured_api_key_name():
    from moamu_ai.errors import ProviderConfigurationError

    try:
        GeminiPhotoJudge(api_key=None, model="gemini-3.5-flash-lite")
    except ProviderConfigurationError as error:
        assert "GEMINI_TOKEN_API_KEY" in str(error)
    else:
        raise AssertionError("missing key should prevent a live provider")


def test_gemini_structured_response_schema_is_supported_by_the_sdk():
    schema = _gemini_response_schema()
    gemini_schema = t_schema(None, schema)

    assert gemini_schema.additional_properties is None
    assert gemini_schema.properties["results"].items.additional_properties is None
