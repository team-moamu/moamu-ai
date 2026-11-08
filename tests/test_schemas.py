import pytest
from pydantic import ValidationError

from moamu_ai.schemas import (
    ConditionResult,
    ConditionStatus,
    PhotoVerificationRequest,
    PhotoVerificationResponse,
)


def test_api_request_uses_image_key_and_only_condition_code_and_description():
    request = PhotoVerificationRequest.model_validate(
        {
            "ai_task_id": "task-1",
            "verification_id": "verification-1",
            "image_key": "verifications/photo.jpg",
            "conditions": [
                {"code": "C1", "description": "컵이 사진에 보여야 한다"},
                {"code": "C2", "description": "손이 컵을 잡고 있어야 한다"},
            ],
        }
    )

    assert request.image_key == "verifications/photo.jpg"
    assert [condition.code for condition in request.conditions] == ["C1", "C2"]


def test_api_request_rejects_duplicate_condition_codes():
    with pytest.raises(ValidationError, match="unique"):
        PhotoVerificationRequest(
            ai_task_id="task-1",
            verification_id="verification-1",
            image_key="proof.jpg",
            conditions=[
                {"code": "C1", "description": "컵이 보인다"},
                {"code": "C1", "description": "손이 보인다"},
            ],
        )


def test_api_request_requires_at_least_one_condition():
    with pytest.raises(ValidationError):
        PhotoVerificationRequest(
            ai_task_id="task-1",
            verification_id="verification-1",
            image_key="proof.jpg",
            conditions=[],
        )


def test_api_response_echoes_ids_and_contains_reason_per_condition():
    response = PhotoVerificationResponse.model_validate(
        {
            "ai_task_id": "task-1",
            "verification_id": "verification-1",
            "processing_status": "SUCCEEDED",
            "checks": [
                {"code": "C1", "status": "MET", "reason": "컵이 확인됩니다."},
                {"code": "C2", "status": "UNCERTAIN", "reason": "손이 가려져 있습니다."},
            ],
            "model_version": "gemini-3.5-flash-lite",
        }
    )

    assert response.checks[1].status is ConditionStatus.UNCERTAIN
    assert response.model_dump(mode="json")["checks"][0]["reason"] == "컵이 확인됩니다."


def test_condition_result_requires_reason_of_at_most_500_characters():
    with pytest.raises(ValidationError):
        ConditionResult(
            challenge_condition_id=1,
            status=ConditionStatus.MET,
            reason="x" * 501,
        )


@pytest.mark.parametrize("status", ["MET", "NOT_MET", "UNCERTAIN"])
def test_condition_status_enum_contains_backend_values(status: str):
    assert ConditionStatus(status).value == status
