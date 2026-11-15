from pydantic import ValidationError

from moamu_ai.errors import InvalidModelOutputError
from moamu_ai.providers.base import GoalAnalyzer
from moamu_ai.schemas import (
    GoalAnalysisOutput,
    GoalVerifiabilityRequest,
    GoalVerifiabilityResponse,
)


class GoalVerifiabilityService:
    """자유목표 분석 모델 결과를 내부 API 응답으로 변환한다."""

    def __init__(self, analyzer: GoalAnalyzer):
        """목표 분석기를 설정한다."""
        self.analyzer = analyzer

    def evaluate(self, request: GoalVerifiabilityRequest) -> GoalVerifiabilityResponse:
        """목표를 분석하고 요청 분류 경로와 응답의 일관성을 확인한다.

        Args:
            request: 원문 목표와 기존 분류 경로를 담은 요청.

        Returns:
            백엔드 내부 API 계약에 맞는 분석 결과.

        Raises:
            InvalidModelOutputError: 모델 출력이나 분류 경로 제안이 계약과 다른 경우.
        """
        try:
            analysis = GoalAnalysisOutput.model_validate(self.analyzer.analyze(request))
        except (ValidationError, TypeError, ValueError) as exc:
            raise InvalidModelOutputError("goal analyzer returned an invalid result") from exc

        if analysis.status == "VERIFIABLE":
            if request.category_path is None and analysis.proposed_category_path is None:
                raise InvalidModelOutputError(
                    "new category path is required for a verifiable goal"
                )
            if request.category_path is not None and analysis.proposed_category_path is not None:
                raise InvalidModelOutputError(
                    "category path proposal is not allowed for an existing path"
                )

        response_data = analysis.model_dump(by_alias=True)
        response_data["goal"] = request.goal
        try:
            return GoalVerifiabilityResponse.model_validate(response_data)
        except ValidationError as exc:
            raise InvalidModelOutputError("goal response does not match the API contract") from exc
