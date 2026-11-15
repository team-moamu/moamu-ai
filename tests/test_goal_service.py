import pytest

from moamu_ai.errors import InvalidModelOutputError
from moamu_ai.goal_service import GoalVerifiabilityService
from moamu_ai.schemas import (
    GoalAnalysisOutput,
    GoalCategoryPath,
    GoalVerifiabilityRequest,
)


class StaticGoalAnalyzer:
    """서비스 테스트에 사용할 고정 자유목표 분석기."""

    def __init__(self, analysis):
        self.analysis = analysis

    def analyze(self, request):
        """저장된 분석 결과를 반환한다."""
        return self.analysis


def verifiable_analysis(proposed_category_path=None):
    """사진 인증이 가능한 목표 분석 결과를 만든다."""
    return GoalAnalysisOutput(
        status="VERIFIABLE",
        normalizedGoal="매일 영어 표현 학습하기",
        proposedCategoryPath=proposed_category_path,
        conditions=["영어 표현을 기록한 흔적이 보여야 한다."],
        photoGuide="기록한 표현이 읽히도록 촬영해 주세요.",
        verificationScope="사진에 남은 표현 기록을 확인합니다.",
        alternatives=[],
    )


def test_service_echoes_goal_and_accepts_category_proposal_when_path_is_null():
    """신규 분류 경로 요청은 제안 경로와 원문 목표를 반환한다."""
    proposed_path = GoalCategoryPath(major="학습", middle="외국어", minor="표현 학습")
    service = GoalVerifiabilityService(StaticGoalAnalyzer(verifiable_analysis(proposed_path)))
    request = GoalVerifiabilityRequest(goal="매일 영어 표현 3개 적기", categoryPath=None)

    response = service.evaluate(request)

    assert response.goal == "매일 영어 표현 3개 적기"
    assert response.normalized_goal == "매일 영어 표현 학습하기"
    assert response.proposed_category_path == proposed_path


def test_service_rejects_missing_category_proposal_for_new_path():
    """신규 경로 요청에서 사진 인증 가능 결과가 경로 제안을 빠뜨리면 거부한다."""
    service = GoalVerifiabilityService(StaticGoalAnalyzer(verifiable_analysis()))
    request = GoalVerifiabilityRequest(goal="매일 영어 표현 적기", categoryPath=None)

    with pytest.raises(InvalidModelOutputError):
        service.evaluate(request)


def test_service_rejects_category_proposal_when_existing_path_was_supplied():
    """기존 분류 경로 요청에서 모델이 새 경로를 제안하면 거부한다."""
    new_path = GoalCategoryPath(major="학습", middle="외국어", minor="표현 학습")
    service = GoalVerifiabilityService(StaticGoalAnalyzer(verifiable_analysis(new_path)))
    request = GoalVerifiabilityRequest(
        goal="매일 영어 표현 적기",
        categoryPath={"major": "학습", "middle": "외국어", "minor": "작문"},
    )

    with pytest.raises(InvalidModelOutputError):
        service.evaluate(request)


def test_service_returns_not_verifiable_result_with_three_alternatives():
    """인증할 수 없는 목표는 모델의 세 가지 대안과 함께 정상 응답한다."""
    analysis = GoalAnalysisOutput(
        status="NOT_VERIFIABLE",
        normalizedGoal=None,
        proposedCategoryPath=None,
        conditions=[],
        photoGuide=None,
        verificationScope=None,
        alternatives=["감사한 일 적기", "고마운 순간 기록하기", "감사 편지 쓰기"],
    )
    service = GoalVerifiabilityService(StaticGoalAnalyzer(analysis))
    request = GoalVerifiabilityRequest(goal="매일 감사한 마음 갖기", categoryPath=None)

    response = service.evaluate(request)

    assert response.status == "NOT_VERIFIABLE"
    assert response.goal == request.goal
    assert len(response.alternatives) == 3
