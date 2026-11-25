"""명화 생성 작업을 Gemini와 S3에 연결한다."""

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Protocol

from moamu_ai.artwork_catalog import (
    ARTWORK_CATALOG,
    ArtworkCatalogEntry,
    select_artwork_source,
)
from moamu_ai.artwork_task_store import (
    ArtworkGenerationTask,
    ArtworkGenerationTaskStore,
)
from moamu_ai.errors import (
    ArtworkGenerationExpiredError,
    ArtworkSourceUnavailableError,
    ImageObjectAlreadyExistsError,
    InvalidModelOutputError,
)
from moamu_ai.providers.base import ArtworkEditor, ArtworkEditResult
from moamu_ai.schemas import ArtworkImageMetadata, ArtworkSourceMetadata


class ArtworkImageStorage(Protocol):
    """원본 조회와 생성 이미지 저장에 필요한 저장소 인터페이스."""

    def open_image(self, image_key: str):
        """이미지 키에 해당하는 임시 로컬 경로를 제공한다."""

    def get_image_if_exists(self, image_key: str) -> Optional[tuple[bytes, str]]:
        """이미 존재하는 이미지가 있으면 바이트와 MIME을 반환한다."""

    def upload_image(self, image_key: str, image_bytes: bytes, content_type: str) -> None:
        """생성 이미지를 객체 저장소에 새 객체로 저장한다."""


class ArtworkGenerationProcessor:
    """카탈로그 원본 편집, S3 업로드와 작업 완료를 처리한다."""

    def __init__(
        self,
        task_store: ArtworkGenerationTaskStore,
        image_storage: ArtworkImageStorage,
        editor: ArtworkEditor,
        catalog: tuple[ArtworkCatalogEntry, ...] = ARTWORK_CATALOG,
    ):
        """생성 처리에 사용할 작업 저장소, 이미지 저장소와 편집기를 설정한다."""
        self.task_store = task_store
        self.image_storage = image_storage
        self.editor = editor
        self.catalog = catalog

    def process(self, task: ArtworkGenerationTask) -> None:
        """작업을 편집하고 결과 메타데이터를 영속화한다."""
        self._ensure_not_expired(task)
        source_entry, source = self._resolve_source(task)

        if task.image is not None and self._recover_uploaded_image(task, source):
            return
        if task.image is not None:
            self.task_store.clear_pending_image(
                task.request.task_id, task.request.task_version
            )

        with self.image_storage.open_image(source_entry.s3_key) as source_path:
            result = self.editor.edit(Path(source_path), task.request)
        self._ensure_not_expired(task)
        self._validate_output(result)

        image = self._image_metadata(task, result)
        self.task_store.save_pending_image(
            task.request.task_id, task.request.task_version, image
        )
        self._ensure_not_expired(task)
        try:
            self.image_storage.upload_image(image.key, result.image_bytes, result.content_type)
        except ImageObjectAlreadyExistsError:
            existing = self.image_storage.get_image_if_exists(image.key)
            if existing is None or not self._matches_metadata(image, *existing):
                raise

        self._ensure_not_expired(task)
        self.task_store.mark_succeeded(
            task.request.task_id,
            task.request.task_version,
            image,
            source,
            reuse_allowed=True,
        )

    def _resolve_source(
        self, task: ArtworkGenerationTask
    ) -> tuple[ArtworkCatalogEntry, ArtworkSourceMetadata]:
        """작업에 이미 저장된 원본을 쓰거나 카탈로그에서 하나를 선택한다."""
        if task.source is None:
            entry = select_artwork_source(task.request, self.catalog)
            source = self.task_store.save_source(
                task.request.task_id,
                task.request.task_version,
                entry.source_metadata(),
            )
        else:
            source = task.source
            entry = next(
                (candidate for candidate in self.catalog if candidate.work_id == source.work_id),
                None,
            )
            if entry is None:
                raise ArtworkSourceUnavailableError("selected source is not in the catalog")
        return entry, source

    def _recover_uploaded_image(
        self, task: ArtworkGenerationTask, source: ArtworkSourceMetadata
    ) -> bool:
        """재시작 전에 업로드가 끝난 이미지를 검사해 모델 재호출을 피한다."""
        image = task.image
        existing = self.image_storage.get_image_if_exists(image.key)
        if existing is None:
            return False
        if not self._matches_metadata(image, *existing):
            raise InvalidModelOutputError("stored artwork does not match saved metadata")
        self.task_store.mark_succeeded(
            task.request.task_id,
            task.request.task_version,
            image,
            source,
            reuse_allowed=True,
        )
        return True

    def _image_metadata(
        self, task: ArtworkGenerationTask, result: ArtworkEditResult
    ) -> ArtworkImageMetadata:
        """작업 버전에 고정된 S3 키와 실제 이미지 메타데이터를 만든다."""
        extension = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/webp": "webp",
        }[result.content_type]
        image_key = (
            f"generated-artworks/{task.request.task_id}/"
            f"{task.request.task_version}/result.{extension}"
        )
        return ArtworkImageMetadata(
            key=image_key,
            contentType=result.content_type,
            sizeBytes=len(result.image_bytes),
            sha256=hashlib.sha256(result.image_bytes).hexdigest(),
        )

    @staticmethod
    def _validate_output(result: ArtworkEditResult) -> None:
        """편집기가 반환한 MIME과 이미지 바이트 서명이 일치하는지 확인한다."""
        detected = _detect_image_content_type(result.image_bytes)
        if not result.image_bytes or detected != result.content_type:
            raise InvalidModelOutputError("Gemini artwork format does not match image bytes")

    @staticmethod
    def _matches_metadata(
        metadata: ArtworkImageMetadata, image_bytes: bytes, content_type: str
    ) -> bool:
        """S3에서 복구한 객체의 MIME, 크기, 해시를 저장한 결과와 대조한다."""
        return (
            content_type == metadata.content_type
            and len(image_bytes) == metadata.size_bytes
            and hashlib.sha256(image_bytes).hexdigest() == metadata.sha256
            and _detect_image_content_type(image_bytes) == metadata.content_type
        )

    @staticmethod
    def _ensure_not_expired(task: ArtworkGenerationTask) -> None:
        """처리 단계마다 작업의 UTC 기한을 확인한다."""
        if task.request.expires_at <= datetime.now(timezone.utc):
            raise ArtworkGenerationExpiredError("artwork generation task expired")


def _detect_image_content_type(image_bytes: bytes) -> Optional[str]:
    """PNG, JPEG 및 WebP 파일 서명에서 MIME 타입을 판별한다."""
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    return None
