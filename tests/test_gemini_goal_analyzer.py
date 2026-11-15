from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from moamu_ai.errors import InvalidModelOutputError
from moamu_ai.providers.gemini import GeminiGoalAnalyzer
from moamu_ai.schemas import GoalVerifiabilityRequest


class FakeGeminiModels:
    """가짜 Gemini 모델 호출과 설정을 기록한다."""

    def __init__(self, response):
        self.response = response
        self.kwargs = None

    def generate_content(self, **kwargs):
        self.kwargs = kwargs
        return self.response


def request():
    """목표 분석에 사용할 신규 분류 요청을 만든다."""
    return GoalVerifiabilityRequest(
        goal="매일 영어 뉴스 10분 듣고 표현 적기",
        category_path=None,
    )


def test_gemini_goal_analyzer_sends_text_and_structured_output_only():
    """Gemini 목표 분석에 목표 텍스트와 JSON 응답 스키마만 보낸다."""
    response = SimpleNamespace(
        text=(
            '{"status":"VERIFIABLE","normalizedGoal":"매일 영어 뉴스 듣기",'
            '"proposedCategoryPath":{"major":"학습","middle":"외국어",'
            '"minor":"듣기 학습"},"conditions":["뉴스에서 들은 표현 기록이 보여야 한다."],'
            '"photoGuide":"기록한 표현이 읽히도록 촬영해 주세요.",'
            '"verificationScope":"사진의 표현 기록을 확인합니다.","alternatives":[]}'
        )
    )
    models = FakeGeminiModels(response)
    analyzer = GeminiGoalAnalyzer(
        api_key=SecretStr("test-key"),
        model="gemini-3.5-flash-lite",
        client=SimpleNamespace(models=models),
    )

    result = analyzer.analyze(request())

    assert result.status == "VERIFIABLE"
    assert models.kwargs["model"] == "gemini-3.5-flash-lite"
    assert isinstance(models.kwargs["contents"], str)
    assert "10분 듣고 표현 적기" in models.kwargs["contents"]
    assert models.kwargs["config"].response_mime_type == "application/json"
    assert models.kwargs["config"].temperature == 0
    assert "normalizedGoal" in models.kwargs["config"].response_schema["properties"]


def test_gemini_goal_analyzer_rejects_inconsistent_structured_output():
    """상태와 맞지 않는 Gemini 응답을 모델 출력 오류로 바꾼다."""
    models = FakeGeminiModels(SimpleNamespace(text='{"status":"NOT_VERIFIABLE"}'))
    analyzer = GeminiGoalAnalyzer(
        api_key=SecretStr("test-key"),
        model="gemini-3.5-flash-lite",
        client=SimpleNamespace(models=models),
    )

    with pytest.raises(InvalidModelOutputError):
        analyzer.analyze(request())

