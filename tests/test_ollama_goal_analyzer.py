import json

import httpx

from moamu_ai.providers.ollama import OllamaGoalAnalyzer
from moamu_ai.schemas import GoalVerifiabilityRequest


def test_ollama_goal_analyzer_sends_text_and_structured_output_schema():
    """Ollama 목표 분석은 텍스트와 구조 스키마를 보내며 이미지는 보내지 않는다."""
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["request"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "message": {
                    "content": (
                        '{"status":"NOT_VERIFIABLE","normalizedGoal":null,'
                        '"proposedCategoryPath":null,"conditions":[],"photoGuide":null,'
                        '"verificationScope":null,"alternatives":["감사한 일 쓰기",'
                        '"고마운 순간 기록하기","감사 편지 쓰기"]}'
                    )
                }
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    analyzer = OllamaGoalAnalyzer(
        base_url="http://localhost:11434/",
        model="qwen3-vl:2b",
        client=client,
    )
    request = GoalVerifiabilityRequest(goal="매일 감사한 마음 갖기", category_path=None)

    result = analyzer.analyze(request)

    assert result.status == "NOT_VERIFIABLE"
    body = seen["request"]
    assert body["model"] == "qwen3-vl:2b"
    assert body["stream"] is False
    assert "매일 감사한 마음 갖기" in body["messages"][0]["content"]
    assert "images" not in body["messages"][0]
    assert "normalizedGoal" in body["format"]["properties"]

