from pathlib import Path

import pytest

from moamu_ai.errors import InvalidModelOutputError
from moamu_ai.image_sources import LocalImageStore
from moamu_ai.providers.base import InferenceResult, InferenceUsage
from moamu_ai.schemas import ConditionResult, ConditionStatus, PhotoVerificationRequest
from moamu_ai.service import PhotoVerificationService


class StaticJudge:
    def __init__(self, results):
        self.results = results
        self.seen_path = None
        self.seen_conditions = None

    def evaluate(self, image_path: Path, conditions):
        self.seen_path = image_path
        self.seen_conditions = conditions
        return InferenceResult(
            results=self.results,
            usage=InferenceUsage(model="gemini-test", latency_ms=0),
        )


def make_request(image_key: str = "proof.jpg") -> PhotoVerificationRequest:
    return PhotoVerificationRequest(
        ai_task_id="task-1",
        verification_id="verification-1",
        image_key=image_key,
        conditions=[
            {"code": "C1", "description": "A water bottle is visible"},
            {"code": "C2", "description": "The person is drinking water"},
        ],
    )


def test_service_validates_image_and_returns_checks_in_request_order(tmp_path: Path):
    root = tmp_path / "images"
    root.mkdir()
    image = root / "proof.jpg"
    image.write_bytes(b"test")
    judge = StaticJudge(
        [
            ConditionResult(
                challenge_condition_id=2,
                status=ConditionStatus.UNCERTAIN,
                reason="행동이 분명하지 않습니다.",
            ),
            ConditionResult(
                challenge_condition_id=1,
                status=ConditionStatus.MET,
                reason="물병이 확인됩니다.",
            ),
        ]
    )
    service = PhotoVerificationService(lambda: judge, LocalImageStore(root))

    response, usage = service.verify_with_usage(make_request())

    assert response.ai_task_id == "task-1"
    assert [item.code for item in response.checks] == ["C1", "C2"]
    assert [item.status for item in response.checks] == [
        ConditionStatus.MET,
        ConditionStatus.UNCERTAIN,
    ]
    assert judge.seen_path == image.resolve()
    assert [(item.code, item.description) for item in judge.seen_conditions] == [
        ("C1", "A water bottle is visible"),
        ("C2", "The person is drinking water"),
    ]
    assert usage.model == "gemini-test"


@pytest.mark.parametrize(
    "results",
    [
        [
            ConditionResult(
                challenge_condition_id=1,
                status=ConditionStatus.MET,
                reason="컵이 보입니다.",
            )
        ],
        [
            ConditionResult(
                challenge_condition_id=1,
                status=ConditionStatus.MET,
                reason="컵이 보입니다.",
            ),
            ConditionResult(
                challenge_condition_id=99,
                status=ConditionStatus.NOT_MET,
                reason="다른 조건입니다.",
            ),
        ],
        [
            ConditionResult(
                challenge_condition_id=1,
                status=ConditionStatus.MET,
                reason="컵이 보입니다.",
            ),
            ConditionResult(
                challenge_condition_id=1,
                status=ConditionStatus.NOT_MET,
                reason="중복 조건입니다.",
            ),
        ],
    ],
)
def test_service_rejects_incomplete_or_mismatched_model_output(tmp_path: Path, results):
    root = tmp_path / "images"
    root.mkdir()
    (root / "proof.jpg").write_bytes(b"test")
    service = PhotoVerificationService(
        lambda: StaticJudge(results),
        LocalImageStore(root),
    )

    with pytest.raises(InvalidModelOutputError):
        service.verify(make_request())
