from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from moamu_ai.schemas import (
    ArtworkGenerationRequest,
    ArtworkGenerationResponse,
)


def generation_request():
    """API 문서의 명화 생성 접수 예시를 만든다."""
    return {
        "taskId": 91,
        "taskVersion": 1,
        "expiresAt": "2026-11-23T04:02:00Z",
        "normalizedGoal": "매일 물 마시기",
        "categoryPath": {"major": "건강", "middle": "생활 습관", "minor": "수분 섭취"},
        "conditions": ["물을 마신 활동 흔적이 사진에서 확인되어야 합니다."],
        "photoGuide": "물과 컵이 보이도록 촬영해 주세요.",
    }


def test_generation_request_accepts_backend_payload_and_utc_expiry():
    request = ArtworkGenerationRequest.model_validate(generation_request())

    assert request.task_id == 91
    assert request.task_version == 1
    assert request.expires_at == datetime(2026, 11, 23, 4, 2, tzinfo=timezone.utc)
    assert request.category_path.minor == "수분 섭취"


@pytest.mark.parametrize(
    "changes",
    [
        {"taskId": 0},
        {"taskVersion": 0},
        {"normalizedGoal": "  "},
        {"conditions": []},
        {"conditions": ["  "]},
        {"photoGuide": "  "},
        {"expiresAt": "2026-11-23T04:02:00"},
        {"unexpected": "field"},
    ],
)
def test_generation_request_rejects_invalid_or_undocumented_values(changes):
    with pytest.raises(ValidationError):
        ArtworkGenerationRequest.model_validate({**generation_request(), **changes})


def test_generation_pending_response_serializes_backend_contract():
    response = ArtworkGenerationResponse.model_validate(
        {"success": True, "data": {"taskId": 91, "taskVersion": 1, "status": "PENDING"}}
    )

    assert response.model_dump(mode="json", by_alias=True) == {
        "success": True,
        "data": {"taskId": 91, "taskVersion": 1, "status": "PENDING"},
    }


def test_generation_success_response_requires_complete_image_and_source_metadata():
    response = ArtworkGenerationResponse.model_validate(
        {
            "success": True,
            "data": {
                "taskId": 91,
                "taskVersion": 1,
                "status": "SUCCEEDED",
                "image": {
                    "key": "generated-artworks/91/1/result.png",
                    "contentType": "image/png",
                    "sizeBytes": 123456,
                    "sha256": "0" * 64,
                },
                "source": {
                    "workId": "museum-123",
                    "title": "원본 명화",
                    "sourceUrl": "https://example.org/work/123",
                    "rightsCode": "PUBLIC_DOMAIN",
                    "rightsUrl": "https://example.org/work/123/rights",
                    "checkedAt": "2026-11-23T04:00:10Z",
                },
                "reuseAllowed": True,
            },
        }
    )

    assert response.data.image.content_type == "image/png"
    assert response.data.source.work_id == "museum-123"
    assert response.data.reuse_allowed is True


def test_generation_success_response_rejects_incomplete_or_invalid_metadata():
    payload = {
        "success": True,
        "data": {
            "taskId": 91,
            "taskVersion": 1,
            "status": "SUCCEEDED",
            "image": {
                "key": "generated-artworks/91/1/result.png",
                "contentType": "image/png",
                "sizeBytes": 123456,
                "sha256": "not-a-sha256",
            },
            "source": {
                "workId": "museum-123",
                "title": "원본 명화",
                "sourceUrl": "https://example.org/work/123",
                "rightsCode": "PUBLIC_DOMAIN",
                "rightsUrl": "https://example.org/work/123/rights",
                "checkedAt": "2026-11-23T04:00:10Z",
            },
            "reuseAllowed": True,
        },
    }

    with pytest.raises(ValidationError):
        ArtworkGenerationResponse.model_validate(payload)


def test_generation_failure_response_requires_retry_metadata():
    response = ArtworkGenerationResponse.model_validate(
        {
            "success": True,
            "data": {
                "taskId": 91,
                "taskVersion": 1,
                "status": "FAILED",
                "errorCode": "ARTWORK_GENERATION_FAILED",
                "retryable": True,
            },
        }
    )

    assert response.data.error_code == "ARTWORK_GENERATION_FAILED"
    assert response.data.retryable is True
