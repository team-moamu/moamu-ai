from pathlib import Path

from moamu_ai.errors import InvalidModelOutputError
from moamu_ai.image_paths import resolve_image_path
from moamu_ai.providers.base import InferenceUsage, JudgeFactory, PhotoJudge
from moamu_ai.schemas import (
    ConditionResult,
    PhotoVerificationRequest,
    PhotoVerificationResponse,
)


class PhotoVerificationService:
    def __init__(self, judge_factory: JudgeFactory, image_root: Path):
        self.judge_factory = judge_factory
        self.image_root = image_root

    def verify(self, request: PhotoVerificationRequest) -> PhotoVerificationResponse:
        response, _ = self.verify_with_usage(request)
        return response

    def verify_with_usage(
        self, request: PhotoVerificationRequest
    ) -> tuple[PhotoVerificationResponse, InferenceUsage]:
        image_path = resolve_image_path(request.image_path, self.image_root)
        judge: PhotoJudge = self.judge_factory()
        inference = judge.evaluate(image_path, request.conditions)

        expected_ids = [item.challenge_condition_id for item in request.conditions]
        received_ids = [item.challenge_condition_id for item in inference.results]
        if len(received_ids) != len(set(received_ids)) or set(received_ids) != set(expected_ids):
            raise InvalidModelOutputError("model result IDs do not match supplied conditions")

        result_by_id: dict[int, ConditionResult] = {
            item.challenge_condition_id: item for item in inference.results
        }
        ordered_results = [result_by_id[condition_id] for condition_id in expected_ids]
        return PhotoVerificationResponse(results=ordered_results), inference.usage
