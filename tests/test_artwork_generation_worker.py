import sqlite3
from datetime import datetime, timedelta, timezone
from threading import Event
from time import monotonic, sleep

import pytest

from moamu_ai.artwork_generation_worker import ArtworkGenerationWorker
from moamu_ai.artwork_task_store import ArtworkGenerationTaskStore
from moamu_ai.errors import ArtworkGenerationExpiredError
from moamu_ai.schemas import ArtworkGenerationRequest, ArtworkImageMetadata, ArtworkSourceMetadata


def request_payload():
    """백그라운드 작업자 테스트용 요청을 만든다."""
    return ArtworkGenerationRequest.model_validate(
        {
            "taskId": 91,
            "taskVersion": 1,
            "expiresAt": (datetime.now(timezone.utc) + timedelta(minutes=2)).isoformat(),
            "normalizedGoal": "매일 물 마시기",
            "categoryPath": {"major": "건강", "middle": "생활 습관", "minor": "수분 섭취"},
            "conditions": ["물이 보인다"],
            "photoGuide": "컵을 보이게 촬영한다.",
        }
    )


def successful_processor(store, completed):
    """작업을 성공 처리하고 완료 이벤트를 알리는 가짜 프로세서다."""

    class Processor:
        """명화 생성 결과를 저장하는 테스트 대역."""

        def process(self, task):
            """작업에 고정된 결과를 기록한다."""
            store.mark_succeeded(
                task.request.task_id,
                task.request.task_version,
                ArtworkImageMetadata(
                    key="generated-artworks/91/1/result.jpg",
                    contentType="image/jpeg",
                    sizeBytes=10,
                    sha256="a" * 64,
                ),
                ArtworkSourceMetadata(
                    workId="test-source",
                    title="Test source",
                    sourceUrl="https://example.org/source",
                    rightsCode="PUBLIC_DOMAIN",
                    rightsUrl="https://example.org/rights",
                    checkedAt=datetime.now(timezone.utc),
                ),
                True,
            )
            completed.set()

    return Processor()


def wait_for_status(store, expected_status):
    """작업 상태가 목표 상태가 될 때까지 제한 시간 안에서 확인한다."""
    deadline = monotonic() + 3
    while monotonic() < deadline:
        task = store.get(91, 1)
        if task.status == expected_status:
            return task
        sleep(0.01)
    pytest.fail(f"task did not reach {expected_status}")


def test_worker_recovers_running_tasks_on_startup(tmp_path):
    """재시작 시 실행 중으로 남은 작업을 다시 실행한다."""
    store = ArtworkGenerationTaskStore(tmp_path / "tasks.sqlite3")
    store.accept(request_payload())
    store.claim(91, 1)
    completed = Event()
    worker = ArtworkGenerationWorker(store, lambda: successful_processor(store, completed))

    worker.start()
    try:
        assert completed.wait(2)
    finally:
        worker.stop()

    assert store.get(91, 1).status == "SUCCEEDED"


def test_worker_deduplicates_a_task_already_queued(tmp_path):
    """같은 작업을 동시에 예약해도 처리기를 한 번만 호출한다."""
    store = ArtworkGenerationTaskStore(tmp_path / "tasks.sqlite3")
    store.accept(request_payload())
    entered = Event()
    release = Event()
    completed = Event()
    calls = []

    class BlockingProcessor:
        """중복 예약을 검사할 수 있도록 작업 실행을 멈춘다."""

        def process(self, task):
            """작업 시작을 알리고 해제된 뒤 성공한다."""
            calls.append(task.request.task_id)
            entered.set()
            assert release.wait(2)
            successful_processor(store, completed).process(task)

    worker = ArtworkGenerationWorker(store, BlockingProcessor)
    worker.start()
    try:
        assert entered.wait(2)
        worker.submit(91, 1)
        release.set()
        assert completed.wait(2)
    finally:
        release.set()
        worker.stop()

    assert calls == [91]
    assert store.get(91, 1).status == "SUCCEEDED"


def test_worker_marks_expired_processing_as_non_retryable(tmp_path):
    """처리 중 기한이 만료되면 재시도 불가 실패 상태로 저장한다."""
    store = ArtworkGenerationTaskStore(tmp_path / "tasks.sqlite3")
    store.accept(request_payload())

    class ExpiredProcessor:
        """작업 기한 초과를 재현하는 프로세서."""

        def process(self, task):
            """기한 만료 예외를 발생시킨다."""
            raise ArtworkGenerationExpiredError("deadline exceeded")

    worker = ArtworkGenerationWorker(store, ExpiredProcessor)
    worker.start()
    try:
        task = wait_for_status(store, "FAILED")
    finally:
        worker.stop()

    response = task.to_response().model_dump(by_alias=True)
    assert response["data"]["errorCode"] == "ARTWORK_TASK_EXPIRED"
    assert response["data"]["retryable"] is False


def test_worker_logs_when_failure_state_cannot_be_saved(monkeypatch, tmp_path, caplog):
    """작업 저장소 장애로 실패 상태를 쓰지 못해도 워커 예외를 남기지 않는다."""
    store = ArtworkGenerationTaskStore(tmp_path / "tasks.sqlite3")
    store.accept(request_payload())
    store.claim(91, 1)

    def fail_mark_failed(*_args):
        raise sqlite3.OperationalError("private database detail")

    monkeypatch.setattr(store, "mark_failed", fail_mark_failed)
    worker = ArtworkGenerationWorker(store, lambda: None)

    worker._mark_failed(91, 1, "ARTWORK_GENERATION_FAILED", True)

    assert "artwork_generation_failure_state_unavailable" in caplog.text
    assert "errorType=OperationalError" in caplog.text
