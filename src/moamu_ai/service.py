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
    def __init__(
        self,
        judge_factory: JudgeFactory,
        image_store: ImageStore,
        model_version: str = "photo-verifier-v1",
    ):
        self.judge_factory = judge_factory
        self.image_store = image_store
        self.model_version = model_version

    def verify(self, request: PhotoVerificationRequest) -> PhotoVerificationResponse:
        response, _ = self.verify_with_usage(request)
        return response

    def verify_with_usage(
        self, request: PhotoVerificationRequest
    ) -> tuple[PhotoVerificationResponse, InferenceUsage]:
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
        """Run a benchmark case from the local evaluation image directory."""
        inference, ordered_results = self._evaluate_image(image_path, conditions)
        return ordered_results, inference.usage

    def _evaluate_image(
        self,
        image_key: str,
        conditions: list[ConditionSnapshot],
    ):
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
