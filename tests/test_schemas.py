import pytest
from pydantic import ValidationError

from moamu_ai.schemas import (
    ConditionResult,
    ConditionSnapshot,
    ConditionStatus,
    PhotoVerificationRequest,
    PhotoVerificationResponse,
)


def condition(condition_id: int) -> ConditionSnapshot:
    return ConditionSnapshot(
        challenge_condition_id=condition_id,
        code=f"condition_{condition_id}",
        condition_type="OBJECT_VISIBLE",
        description=f"Object {condition_id} is visible",
        required=True,
        sort_order=condition_id,
    )


def test_request_accepts_two_or_three_conditions_and_rejects_duplicate_ids():
    request = PhotoVerificationRequest(
        image_path="proof.jpg",
        conditions=[condition(1), condition(2)],
    )

    assert len(request.conditions) == 2
    with pytest.raises(ValidationError):
        PhotoVerificationRequest(
            image_path="proof.jpg",
            conditions=[condition(1), condition(1)],
        )


@pytest.mark.parametrize("count", [1, 4])
def test_request_requires_two_or_three_conditions(count: int):
    with pytest.raises(ValidationError):
        PhotoVerificationRequest(
            image_path="proof.jpg",
            conditions=[condition(index) for index in range(1, count + 1)],
        )


def test_request_requires_at_least_two_required_conditions():
    optional_condition = condition(2).model_copy(update={"required": False})

    with pytest.raises(ValidationError, match="at least two conditions must be required"):
        PhotoVerificationRequest(
            image_path="proof.jpg",
            conditions=[condition(1), optional_condition],
        )


def test_response_contains_only_condition_identity_and_status():
    response = PhotoVerificationResponse.model_validate(
        {
            "results": [
                {
                    "challenge_condition_id": 1,
                    "status": "MET",
                },
                {"challenge_condition_id": 2, "status": "UNCERTAIN"},
            ]
        }
    )

    assert response.model_dump(mode="json") == {
        "results": [
            {"challenge_condition_id": 1, "status": "MET"},
            {"challenge_condition_id": 2, "status": "UNCERTAIN"},
        ]
    }
    assert set(ConditionStatus) == {
        ConditionStatus.MET,
        ConditionStatus.NOT_MET,
        ConditionStatus.UNCERTAIN,
    }


def test_condition_result_still_rejects_non_positive_ids():
    with pytest.raises(ValidationError, match="challenge_condition_id must be positive"):
        ConditionResult(challenge_condition_id=0, status=ConditionStatus.MET)
