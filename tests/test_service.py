from pathlib import Path

import pytest

from moamu_ai.errors import InvalidModelOutputError
from moamu_ai.providers.base import InferenceResult, InferenceUsage
from moamu_ai.schemas import (
    ConditionResult,
    ConditionSnapshot,
    ConditionStatus,
    PhotoVerificationRequest,
)
from moamu_ai.service import PhotoVerificationService


class StaticJudge:
    def __init__(self, results):
        self.results = results
        self.seen_path = None
        self.seen_conditions = None

    def evaluate(self, image_path: Path, conditions: list[ConditionSnapshot]):
        self.seen_path = image_path
        self.seen_conditions = conditions
        return InferenceResult(
            results=self.results,
            usage=InferenceUsage(model="fake", latency_ms=0),
        )


def make_request(image_path: str) -> PhotoVerificationRequest:
    return PhotoVerificationRequest(
        image_path=image_path,
        conditions=[
            ConditionSnapshot(
                challenge_condition_id=10,
                code="OBJECT_VISIBLE",
                condition_type="OBJECT_VISIBLE",
                description="A water bottle is visible",
                required=True,
                sort_order=1,
            ),
            ConditionSnapshot(
                challenge_condition_id=11,
                code="ACTION_VISIBLE",
                condition_type="ACTION_VISIBLE",
                description="The person is drinking water",
                required=True,
                sort_order=2,
            ),
        ],
    )


def test_service_validates_path_and_preserves_condition_order(tmp_path: Path):
    root = tmp_path / "images"
    root.mkdir()
    image = root / "proof.jpg"
    image.write_bytes(b"test")
    expected = [
        ConditionResult(challenge_condition_id=10, status=ConditionStatus.MET),
        ConditionResult(challenge_condition_id=11, status=ConditionStatus.UNCERTAIN),
    ]
    judge = StaticJudge(expected)

    response = PhotoVerificationService(lambda: judge, root).verify(make_request("proof.jpg"))

    assert response.results == expected
    assert judge.seen_path == image.resolve()
    assert [item.challenge_condition_id for item in judge.seen_conditions] == [10, 11]


@pytest.mark.parametrize(
    "results",
    [
        [ConditionResult(challenge_condition_id=10, status=ConditionStatus.MET)],
        [
            ConditionResult(challenge_condition_id=10, status=ConditionStatus.MET),
            ConditionResult(challenge_condition_id=99, status=ConditionStatus.NOT_MET),
        ],
        [
            ConditionResult(challenge_condition_id=10, status=ConditionStatus.MET),
            ConditionResult(challenge_condition_id=10, status=ConditionStatus.NOT_MET),
        ],
    ],
)
def test_service_rejects_incomplete_or_mismatched_model_output(tmp_path: Path, results):
    root = tmp_path / "images"
    root.mkdir()
    (root / "proof.jpg").write_bytes(b"test")

    service = PhotoVerificationService(lambda: StaticJudge(results), root)

    with pytest.raises(InvalidModelOutputError):
        service.verify(make_request("proof.jpg"))
