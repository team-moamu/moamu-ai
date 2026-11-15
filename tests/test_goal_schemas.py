import pytest
from pydantic import ValidationError

from moamu_ai.schemas import (
    GoalAnalysisErrorResponse,
    GoalAnalysisOutput,
    GoalCategoryPath,
    GoalVerifiabilityRequest,
    GoalVerifiabilityResponse,
)


def test_goal_request_accepts_existing_path_and_serializes_as_camel_case():
    """기존 분류 경로를 camelCase 요청으로 읽는다."""
    request = GoalVerifiabilityRequest.model_validate(
        {
            "goal": "매일 일본어 단어장 만들기",
            "categoryPath": {
                "major": "학습",
                "middle": "외국어",
                "minor": "어휘 학습",
            },
        }
    )

    assert request.category_path == GoalCategoryPath(
        major="학습", middle="외국어", minor="어휘 학습"
    )
    assert request.model_dump(by_alias=True)["categoryPath"]["minor"] == "어휘 학습"


def test_goal_request_requires_category_path_to_be_present_but_allows_null():
    """신규 경로 분석을 위해 categoryPath 누락과 명시적 null을 구분한다."""
    request = GoalVerifiabilityRequest.model_validate(
        {"goal": "영어 뉴스 듣고 표현 기록하기", "categoryPath": None}
    )

    assert request.category_path is None
    with pytest.raises(ValidationError):
        GoalVerifiabilityRequest.model_validate({"goal": "영어 뉴스 듣기"})


@pytest.mark.parametrize("goal", ["", "   "])
def test_goal_request_rejects_empty_or_whitespace_goal(goal):
    """사진 인증 분석에 빈 목표 문장을 허용하지 않는다."""
    with pytest.raises(ValidationError):
        GoalVerifiabilityRequest.model_validate({"goal": goal, "categoryPath": None})


def test_goal_contract_does_not_add_undocumented_text_length_limits():
    """내부 API 명세에 상한이 없는 목표·분류명·대안 길이를 허용한다."""
    goal = "목표" + ("가" * 1000)
    category_path = {
        "major": "대" * 101,
        "middle": "중분류",
        "minor": "소분류",
    }
    request = GoalVerifiabilityRequest.model_validate(
        {"goal": goal, "categoryPath": category_path}
    )
    analysis = GoalAnalysisOutput.model_validate(
        {
            "status": "NOT_VERIFIABLE",
            "normalizedGoal": None,
            "proposedCategoryPath": None,
            "conditions": [],
            "photoGuide": None,
            "verificationScope": None,
            "alternatives": ["대안" + ("가" * 500), "대안 둘", "대안 셋"],
        }
    )

    assert request.goal == goal
    assert len(analysis.alternatives[0]) == 502


def test_verifiable_goal_output_requires_evidence_fields_and_no_alternatives():
    """인증 가능한 목표 출력에 조건과 촬영 정보를 요구한다."""
    output = GoalAnalysisOutput.model_validate(
        {
            "status": "VERIFIABLE",
            "normalizedGoal": "매일 영어 단어 학습하기",
            "proposedCategoryPath": {
                "major": "학습",
                "middle": "외국어",
                "minor": "어휘 학습",
            },
            "conditions": ["외국어 단어와 학습 흔적이 사진에서 확인되어야 합니다."],
            "photoGuide": "단어와 메모가 읽히도록 촬영해 주세요.",
            "verificationScope": "사진에 보이는 학습 흔적을 확인합니다.",
            "alternatives": [],
        }
    )

    assert output.status == "VERIFIABLE"
    assert output.model_dump(by_alias=True)["normalizedGoal"] == "매일 영어 단어 학습하기"


def test_not_verifiable_output_requires_exactly_three_alternatives():
    """인증할 수 없는 목표는 대안 세 개와 null 인증 필드를 반환한다."""
    output = GoalAnalysisOutput.model_validate(
        {
            "status": "NOT_VERIFIABLE",
            "normalizedGoal": None,
            "proposedCategoryPath": None,
            "conditions": [],
            "photoGuide": None,
            "verificationScope": None,
            "alternatives": ["감사한 일 쓰기", "고마운 순간 기록하기", "감사 편지 쓰기"],
        }
    )

    assert len(output.alternatives) == 3


def test_goal_output_rejects_inconsistent_status_fields():
    """판정 상태에 맞지 않는 인증 정보 조합을 거부한다."""
    with pytest.raises(ValidationError):
        GoalAnalysisOutput.model_validate(
            {
                "status": "NOT_VERIFIABLE",
                "normalizedGoal": "정리된 목표",
                "proposedCategoryPath": None,
                "conditions": [],
                "photoGuide": None,
                "verificationScope": None,
                "alternatives": ["대안 하나", "대안 둘", "대안 셋"],
            }
        )


def test_goal_response_echoes_original_goal_in_public_contract():
    """API 응답은 원문 목표와 camelCase 필드명을 반환한다."""
    response = GoalVerifiabilityResponse.model_validate(
        {
            "goal": "매일 영어 단어 20개 외우기",
            "status": "VERIFIABLE",
            "normalizedGoal": "매일 영어 단어 학습하기",
            "proposedCategoryPath": None,
            "conditions": ["단어 학습 흔적이 사진에서 확인되어야 합니다."],
            "photoGuide": "단어와 메모가 읽히도록 촬영해 주세요.",
            "verificationScope": "사진에 보이는 학습 흔적을 확인합니다.",
            "alternatives": [],
        }
    )

    assert response.model_dump(by_alias=True)["goal"] == "매일 영어 단어 20개 외우기"
    assert "photoGuide" in response.model_dump(by_alias=True)


def test_goal_error_response_matches_internal_api_contract():
    """목표 분석 오류 응답은 내부 API의 code/message 형식을 사용한다."""
    response = GoalAnalysisErrorResponse.model_validate(
        {"code": "AI_MODEL_UNAVAILABLE", "message": "모델을 사용할 수 없습니다."}
    )

    assert response.model_dump() == {
        "code": "AI_MODEL_UNAVAILABLE",
        "message": "모델을 사용할 수 없습니다.",
    }
