import base64
import json
from pathlib import Path

import httpx

from moamu_ai.providers.ollama import OllamaPhotoJudge
from moamu_ai.schemas import ConditionSnapshot, ConditionStatus


def test_ollama_sends_local_image_with_a_constrained_response_schema(tmp_path: Path):
    image_path = tmp_path / "proof.jpg"
    image_path.write_bytes(b"local test image")
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["request"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "message": {
                    "content": (
                        '{"results":[{"challenge_condition_id":1,"status":"UNCERTAIN"},'
                        '{"challenge_condition_id":2,"status":"MET"}]}'
                    )
                },
                "prompt_eval_count": 30,
                "eval_count": 6,
                "total_duration": 400000000,
            },
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    judge = OllamaPhotoJudge(
        base_url="http://localhost:11434/",
        model="qwen3-vl:2b",
        client=http_client,
    )
    conditions = [
        ConditionSnapshot(
            challenge_condition_id=1,
            code="WATER_BOTTLE",
            condition_type="OBJECT_VISIBLE",
            description="A bottle is visible",
            required=True,
            sort_order=1,
        ),
        ConditionSnapshot(
            challenge_condition_id=2,
            code="DRINKING",
            condition_type="ACTION_VISIBLE",
            description="A drinking action is visible",
            required=True,
            sort_order=2,
        ),
    ]

    result = judge.evaluate(image_path, conditions)

    assert result.results[0].status == ConditionStatus.UNCERTAIN
    assert result.usage.prompt_tokens == 30
    assert result.usage.total_tokens == 36
    request_body = seen["request"]
    assert request_body["model"] == "qwen3-vl:2b"
    assert request_body["stream"] is False
    assert request_body["options"]["temperature"] == 0
    assert request_body["messages"][0]["images"] == [
        base64.b64encode(b"local test image").decode("ascii")
    ]
    assert request_body["format"]["$defs"]["ConditionStatus"]["enum"] == [
        "MET",
        "NOT_MET",
        "UNCERTAIN",
    ]
