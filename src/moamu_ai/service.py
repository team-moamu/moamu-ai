from pathlib import Path

from moamu_ai.errors import InvalidModelOutputError
from moamu_ai.image_sources import ImageStore
from moamu_ai.providers.base import InferenceUsage, JudgeFactory, PhotoJudge
from moamu_ai.schemas import (
    ConditionCheck,
    ConditionResult,
    ConditionSnapshot,
    PhotoVerificationRequest,
    PhotoVerificationResponse,
)


class PhotoVerificationService:
    """이미지 조회, 모델 판정, API 응답 생성을 조정한다."""

    def __init__(
        self,
        judge_factory: JudgeFactory,
        image_store: ImageStore,
        model_version: str = "photo-verifier-v1",
    ):
        """판정 모델 생성기, 이미지 저장소, 모델 버전을 설정한다."""
        self.judge_factory = judge_factory
        self.image_store = image_store
        self.model_version = model_version

    def verify(self, request: PhotoVerificationRequest) -> PhotoVerificationResponse:
        """요청을 판정하고 API 성공 응답만 반환한다.

        Args:
            request: 이미지 키와 인증 조건이 담긴 API 요청.

        Returns:
            조건별 판정이 포함된 API 응답.
        """
        response, _ = self.verify_with_usage(request)
        return response

    def verify_with_usage(
        self, request: PhotoVerificationRequest
    ) -> tuple[PhotoVerificationResponse, InferenceUsage]:
        """요청을 판정하고 응답과 모델 사용량을 함께 반환한다.

        Args:
            request: 이미지 키와 인증 조건이 담긴 API 요청.

        Returns:
            API 응답과 모델 추론 사용량의 쌍.
        """
        model_conditions = [
            ConditionSnapshot(
                challenge_condition_id=index,
                code=condition.code,
                condition_type="BACKEND_CONDITION",
                description=condition.description,
                required=True,
                sort_order=index,
            )
            for index, condition in enumerate(request.conditions, start=1)
        ]
        inference, ordered_results = self._evaluate_image(
            request.image_key,
            model_conditions,
        )
        result_by_id = {
            result.challenge_condition_id: result for result in ordered_results
        }
        checks = [
            ConditionCheck(
                code=condition.code,
                status=result_by_id[index].status,
                reason=result_by_id[index].reason,
            )
            for index, condition in enumerate(request.conditions, start=1)
        ]
        response = PhotoVerificationResponse(
            ai_task_id=request.ai_task_id,
            verification_id=request.verification_id,
            processing_status="SUCCEEDED",
            checks=checks,
            model_version=self.model_version,
        )
        return response, inference.usage

    def evaluate_local_with_usage(
        self,
        image_path: str,
        conditions: list[ConditionSnapshot],
    ) -> tuple[list[ConditionResult], InferenceUsage]:
        """로컬 평가 이미지 사례를 판정하고 결과와 사용량을 반환한다.

        Args:
            image_path: 평가 이미지의 저장소 키 또는 경로.
            conditions: 평가할 인증 조건 목록.

        Returns:
            조건별 판정 결과 목록과 모델 추론 사용량.
        """
        inference, ordered_results = self._evaluate_image(image_path, conditions)
        return ordered_results, inference.usage

    def _evaluate_image(
        self,
        image_key: str,
        conditions: list[ConditionSnapshot],
    ):
        """이미지를 열어 모델 판정을 수행하고 조건 순서로 결과를 정리한다.

        Args:
            image_key: 이미지 저장소에서 사용할 객체 키 또는 경로.
            conditions: 모델이 판정할 인증 조건 목록.

        Returns:
            모델 응답과 입력 조건 순서로 정렬된 판정 목록.

        Raises:
            InvalidModelOutputError: 모델 결과 ID가 조건 목록과 일치하지 않는 경우.
        """
        with self.image_store.open_image(image_key) as image_path:
            judge: PhotoJudge = self.judge_factory()
            inference = judge.evaluate(Path(image_path), conditions)

        expected_ids = [condition.challenge_condition_id for condition in conditions]
        received_ids = [result.challenge_condition_id for result in inference.results]
        if (
            len(received_ids) != len(set(received_ids))
            or set(received_ids) != set(expected_ids)
        ):
            raise InvalidModelOutputError(
                "model result IDs do not match supplied conditions"
            )

        result_by_id = {
            result.challenge_condition_id: result for result in inference.results
        }
        ordered_results = [result_by_id[condition_id] for condition_id in expected_ids]
        return inference, ordered_results
