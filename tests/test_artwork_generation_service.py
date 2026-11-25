import hashlib
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from moamu_ai.artwork_catalog import ARTWORK_CATALOG
from moamu_ai.artwork_generation_service import ArtworkGenerationProcessor
from moamu_ai.artwork_task_store import ArtworkGenerationTaskStore
from moamu_ai.errors import ArtworkSourceUnavailableError
from moamu_ai.providers.base import ArtworkEditResult
from moamu_ai.schemas import ArtworkGenerationRequest, ArtworkImageMetadata

JPEG_BYTES = b"\xff\xd8\xffmock-jpeg-image"


def request_payload():
    """생성 처리 테스트에 사용할 유효한 요청을 만든다."""
    return ArtworkGenerationRequest.model_validate(
        {
            "taskId": 91,
            "taskVersion": 1,
            "expiresAt": (datetime.now(timezone.utc) + timedelta(minutes=2)).isoformat(),
            "normalizedGoal": "매일 물 마시기",
            "categoryPath": {"major": "건강", "middle": "생활 습관", "minor": "수분 섭취"},
            "conditions": ["물이 보여야 한다", "물을 마시는 장면이 보여야 한다"],
            "photoGuide": "사람과 컵이 함께 보이게 촬영한다.",
        }
    )


class FakeImageStore:
    """원본 읽기와 결과 업로드를 메모리에서 제공한다."""

    def __init__(self, source_path: Path):
        self.source_path = source_path
        self.opened_keys = []
        self.uploaded = {}

    @contextmanager
    def open_image(self, image_key: str):
        """요청된 S3 키에 대응하는 테스트 원본 경로를 제공한다."""
        self.opened_keys.append(image_key)
        yield self.source_path

    def get_image_if_exists(self, image_key: str):
        """이미 저장된 객체가 있으면 바이트와 MIME을 반환한다."""
        return self.uploaded.get(image_key)

    def upload_image(self, image_key: str, image_bytes: bytes, content_type: str):
        """테스트 결과 객체를 덮어쓰지 않고 저장한다."""
        if image_key in self.uploaded:
            raise AssertionError("the test store does not allow overwriting objects")
        self.uploaded[image_key] = (image_bytes, content_type)


class FakeArtworkEditor:
    """편집 결과를 고정된 이미지 바이트로 반환한다."""

    def __init__(self):
        self.calls = []

    def edit(self, image_path: Path, request: ArtworkGenerationRequest):
        """요청된 목표를 기록하고 JPEG 결과를 반환한다."""
        self.calls.append((image_path, request.task_id))
        return ArtworkEditResult(
            image_bytes=JPEG_BYTES,
            content_type="image/jpeg",
            model="gemini-test",
            latency_ms=1.0,
        )


def test_process_generates_uploads_and_persists_metadata(tmp_path):
    """작업 원본을 편집하고 버전별 S3 키와 해시를 저장한다."""
    source_path = tmp_path / "source.jpg"
    source_path.write_bytes(b"source painting")
    image_store = FakeImageStore(source_path)
    editor = FakeArtworkEditor()
    task_store = ArtworkGenerationTaskStore(tmp_path / "tasks.sqlite3")
    task_store.accept(request_payload())
    claimed_task = task_store.claim(91, 1)
    processor = ArtworkGenerationProcessor(task_store, image_store, editor)

    processor.process(claimed_task)

    task = task_store.get(91, 1)
    assert task.status == "SUCCEEDED"
    assert task.image.key == "generated-artworks/91/1/result.jpg"
    assert task.image.content_type == "image/jpeg"
    assert task.image.size_bytes == len(JPEG_BYTES)
    assert task.image.sha256 == hashlib.sha256(JPEG_BYTES).hexdigest()
    assert task.source.work_id == ARTWORK_CATALOG[0].work_id
    assert image_store.opened_keys == [ARTWORK_CATALOG[0].s3_key]
    assert list(image_store.uploaded) == [task.image.key]
    assert len(editor.calls) == 1


def test_process_recovers_an_object_uploaded_before_worker_restart(tmp_path):
    """업로드 후 프로세스가 중단됐으면 같은 객체를 확인해 생성 호출을 생략한다."""
    source_path = tmp_path / "source.jpg"
    source_path.write_bytes(b"source painting")
    image_store = FakeImageStore(source_path)
    editor = FakeArtworkEditor()
    task_store = ArtworkGenerationTaskStore(tmp_path / "tasks.sqlite3")
    task_store.accept(request_payload())
    task_store.claim(91, 1)
    source = ARTWORK_CATALOG[0].source_metadata()
    task_store.save_source(91, 1, source)
    image_key = "generated-artworks/91/1/result.jpg"
    image = {
        "key": image_key,
        "contentType": "image/jpeg",
        "sizeBytes": len(JPEG_BYTES),
        "sha256": hashlib.sha256(JPEG_BYTES).hexdigest(),
    }
    image_store.uploaded[image_key] = (JPEG_BYTES, "image/jpeg")
    task_store.save_pending_image(91, 1, ArtworkImageMetadata.model_validate(image))
    task_store.recover_interrupted()
    claimed_task = task_store.claim(91, 1)
    processor = ArtworkGenerationProcessor(task_store, image_store, editor)

    processor.process(claimed_task)

    assert task_store.get(91, 1).status == "SUCCEEDED"
    assert len(editor.calls) == 0


def test_process_reports_missing_rights_checked_source_as_unavailable(tmp_path):
    """사용 가능한 권리 확인 원본이 없으면 작업을 재시도 불가 실패로 분류한다."""
    source_path = tmp_path / "source.jpg"
    source_path.write_bytes(b"source painting")
    task_store = ArtworkGenerationTaskStore(tmp_path / "tasks.sqlite3")
    task_store.accept(request_payload())
    claimed_task = task_store.claim(91, 1)
    processor = ArtworkGenerationProcessor(
        task_store,
        FakeImageStore(source_path),
        FakeArtworkEditor(),
        catalog=(),
    )

    with pytest.raises(ArtworkSourceUnavailableError):
        processor.process(claimed_task)
