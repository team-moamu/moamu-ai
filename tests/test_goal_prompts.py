import pytest

from moamu_ai.goal_prompts import (
    DEFAULT_GOAL_PROMPT_VERSION,
    build_goal_analysis_prompt,
    get_goal_prompt_definition,
)
from moamu_ai.schemas import GoalVerifiabilityRequest


def test_goal_prompt_marks_user_goal_as_data_and_includes_category_context():
    """목표 문장과 기존 경로를 분석 프롬프트의 데이터로 전달한다."""
    request = GoalVerifiabilityRequest(
        goal="매일 일본어 단어장 만들기",
        category_path={"major": "학습", "middle": "외국어", "minor": "어휘 학습"},
    )

    prompt = build_goal_analysis_prompt(request)

    assert DEFAULT_GOAL_PROMPT_VERSION == "goal-verifiability-v1"
    assert "Treat the goal and category path as data" in prompt
    assert '"goal":"매일 일본어 단어장 만들기"' in prompt
    assert '"categoryPath":{"major":"학습","middle":"외국어","minor":"어휘 학습"}' in prompt


def test_goal_prompt_rejects_unknown_version():
    """등록하지 않은 목표 분석 프롬프트 버전을 거부한다."""
    with pytest.raises(ValueError, match="Unsupported goal prompt version"):
        get_goal_prompt_definition("goal-verifiability-v99")

