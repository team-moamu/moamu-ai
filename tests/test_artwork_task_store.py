from datetime import datetime, timedelta, timezone

import pytest

from moamu_ai.artwork_task_store import (
    ArtworkGenerationTaskStore,
    ArtworkTaskPayloadConflictError,
)
from moamu_ai.schemas import (
    ArtworkGenerationRequest,
    ArtworkImageMetadata,
    ArtworkSourceMetadata,
)


def request_payload(**overrides):
    """작업 저장소 테스트에 사용할 명화 생성 요청을 만든다."""
    payload = {
        "taskId": 91,
        "taskVersion": 1,
        "expiresAt": (datetime.now(timezone.utc) + timedelta(minutes=2)).isoformat(),
        "normalizedGoal": "매일 물 마시기",
        "categoryPath": {"major": "건강", "middle": "생활 습관", "minor": "수분 섭취"},
        "conditions": ["물이 보인다", "물을 마시는 장면이 보인다"],
        "photoGuide": "컵과 사람이 함께 보이게 촬영한다.",
    }
    payload.update(overrides)
    return payload


def source_metadata():
    """작업 성공 응답용 출처 정보를 만든다."""
    return ArtworkSourceMetadata(
        workId="nga-1942.9.97",
        title="Woman Holding a Balance",
        sourceUrl="https://www.nga.gov/artworks/1236-woman-holding-balance",
        rightsCode="PUBLIC_DOMAIN",
        rightsUrl="https://www.nga.gov/artworks/1236-woman-holding-balance",
        checkedAt=datetime(2026, 11, 24, tzinfo=timezone.utc),
    )


def image_metadata():
    """작업 성공 응답용 S3 객체 정보를 만든다."""
    return ArtworkImageMetadata(
        key="generated-artworks/91/1/result.jpg",
        contentType="image/jpeg",
        sizeBytes=1234,
        sha256="a" * 64,
    )


def test_accept_returns_same_task_for_same_key_and_payload(tmp_path):
    """같은 작업 키와 본문을 다시 접수하면 기존 작업을 반환한다."""
    store = ArtworkGenerationTaskStore(tmp_path / "artwork-tasks.sqlite3")
    request = ArtworkGenerationRequest.model_validate(request_payload())

    first, first_created = store.accept(request)
    second, second_created = store.accept(request)

    assert first_created is True
    assert second_created is False
    assert second.status == "PENDING"
    assert second.request.task_id == 91
    assert second.request.task_version == 1


def test_accept_rejects_same_key_with_different_payload(tmp_path):
    """같은 작업 키에 다른 본문을 보내면 충돌로 거부한다."""
    store = ArtworkGenerationTaskStore(tmp_path / "artwork-tasks.sqlite3")
    store.accept(ArtworkGenerationRequest.model_validate(request_payload()))

    with pytest.raises(ArtworkTaskPayloadConflictError):
        store.accept(
            ArtworkGenerationRequest.model_validate(
                request_payload(normalizedGoal="매일 차 마시기")
            )
        )


def test_claim_allows_only_one_worker_and_marks_task_running(tmp_path):
    """대기 작업을 원자적으로 선점해 한 워커만 실행한다."""
    store = ArtworkGenerationTaskStore(tmp_path / "artwork-tasks.sqlite3")
    store.accept(ArtworkGenerationRequest.model_validate(request_payload()))

    first_claim = store.claim(91, 1)
    second_claim = store.claim(91, 1)

    assert first_claim is not None
    assert first_claim.status == "RUNNING"
    assert second_claim is None


def test_success_result_is_persisted_and_returned_in_contract_shape(tmp_path):
    """성공 결과의 이미지·출처 메타데이터를 재시작 뒤에도 반환한다."""
    database_path = tmp_path / "artwork-tasks.sqlite3"
    store = ArtworkGenerationTaskStore(database_path)
    store.accept(ArtworkGenerationRequest.model_validate(request_payload()))
    store.claim(91, 1)
    store.mark_succeeded(91, 1, image_metadata(), source_metadata(), True)

    reopened_store = ArtworkGenerationTaskStore(database_path)
    response = reopened_store.get(91, 1).to_response().model_dump(by_alias=True)

    assert response["data"]["status"] == "SUCCEEDED"
    assert response["data"]["image"]["key"] == "generated-artworks/91/1/result.jpg"
    assert response["data"]["source"]["workId"] == "nga-1942.9.97"
    assert response["data"]["reuseAllowed"] is True


def test_failed_result_is_persisted_with_retryability(tmp_path):
    """실패 상태와 재시도 가능 여부를 저장한다."""
    store = ArtworkGenerationTaskStore(tmp_path / "artwork-tasks.sqlite3")
    store.accept(ArtworkGenerationRequest.model_validate(request_payload()))
    store.claim(91, 1)
    store.mark_failed(91, 1, "ARTWORK_GENERATION_FAILED", True)

    response = store.get(91, 1).to_response().model_dump(by_alias=True)

    assert response["data"] == {
        "taskId": 91,
        "taskVersion": 1,
        "status": "FAILED",
        "errorCode": "ARTWORK_GENERATION_FAILED",
        "retryable": True,
    }


def test_running_task_is_reset_to_pending_for_restart_recovery(tmp_path):
    """프로세스 재시작 시 미완료 작업을 다시 처리할 수 있게 한다."""
    database_path = tmp_path / "artwork-tasks.sqlite3"
    first_store = ArtworkGenerationTaskStore(database_path)
    first_store.accept(ArtworkGenerationRequest.model_validate(request_payload()))
    first_store.claim(91, 1)

    recovered_store = ArtworkGenerationTaskStore(database_path)
    recovered_store.recover_interrupted()

    task = recovered_store.get(91, 1)
    assert task.status == "PENDING"
    assert [pending.request.task_id for pending in recovered_store.list_pending()] == [91]
