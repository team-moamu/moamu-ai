"""명화 생성 작업을 SQLite에 보관한다."""

import hashlib
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

from moamu_ai.schemas import (
    ArtworkGenerationRequest,
    ArtworkGenerationResponse,
    ArtworkImageMetadata,
    ArtworkSourceMetadata,
)


class ArtworkTaskPayloadConflictError(Exception):
    """같은 작업 키에 다른 요청 본문이 전달된 경우 발생한다."""


class ArtworkTaskExpiredError(Exception):
    """신규 접수 시점에 작업 기한이 지난 경우 발생한다."""


@dataclass(frozen=True)
class ArtworkGenerationTask:
    """저장된 작업의 입력, 상태 및 생성 결과를 나타낸다."""

    request: ArtworkGenerationRequest
    status: str
    source: Optional[ArtworkSourceMetadata] = None
    image: Optional[ArtworkImageMetadata] = None
    reuse_allowed: Optional[bool] = None
    error_code: Optional[str] = None
    retryable: Optional[bool] = None

    def to_response(self) -> ArtworkGenerationResponse:
        """저장된 작업 상태를 백엔드 API 응답 모델로 변환한다."""
        data = {
            "taskId": self.request.task_id,
            "taskVersion": self.request.task_version,
            "status": self.status,
        }
        if self.status == "SUCCEEDED":
            data.update(
                {
                    "image": self.image.model_dump(mode="json", by_alias=True),
                    "source": self.source.model_dump(mode="json", by_alias=True),
                    "reuseAllowed": self.reuse_allowed,
                }
            )
        elif self.status == "FAILED":
            data.update(
                {
                    "errorCode": self.error_code,
                    "retryable": self.retryable,
                }
            )
        return ArtworkGenerationResponse.model_validate({"success": True, "data": data})


class ArtworkGenerationTaskStore:
    """SQLite 파일에 명화 작업을 멱등하게 저장한다."""

    def __init__(self, database_path: Union[Path, str]):
        """작업 데이터베이스를 만들거나 기존 데이터베이스를 연다."""
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        """SQLite 연결을 열고 작업 후 닫는다."""
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 30000")
        try:
            yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        """작업 테이블과 디스크 저널 모드를 준비한다."""
        with self._connection() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS artwork_generation_tasks (
                    task_id INTEGER NOT NULL,
                    task_version INTEGER NOT NULL,
                    request_json TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (
                        status IN ('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED')
                    ),
                    source_json TEXT,
                    image_json TEXT,
                    reuse_allowed INTEGER,
                    error_code TEXT,
                    retryable INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (task_id, task_version)
                )
                """
            )

    @staticmethod
    def _request_json(request: ArtworkGenerationRequest) -> str:
        """비교 및 저장을 위해 요청을 안정된 JSON 문자열로 직렬화한다."""
        return json.dumps(
            request.model_dump(mode="json", by_alias=True),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def _now() -> str:
        """현재 UTC 시각을 저장 가능한 문자열로 반환한다."""
        return datetime.now(timezone.utc).isoformat()

    def accept(
        self, request: ArtworkGenerationRequest
    ) -> tuple[ArtworkGenerationTask, bool]:
        """작업을 영속화하고 동일 요청이면 기존 작업을 반환한다."""
        request_json = self._request_json(request)
        request_hash = hashlib.sha256(request_json.encode("utf-8")).hexdigest()
        now = self._now()
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT * FROM artwork_generation_tasks
                WHERE task_id = ? AND task_version = ?
                """,
                (request.task_id, request.task_version),
            ).fetchone()
            if row is not None:
                if row["request_hash"] != request_hash:
                    connection.rollback()
                    raise ArtworkTaskPayloadConflictError(
                        "task key was already accepted with a different payload"
                    )
                connection.commit()
                return self._task_from_row(row), False

            if request.expires_at <= datetime.now(timezone.utc):
                connection.rollback()
                raise ArtworkTaskExpiredError("artwork generation request has expired")

            connection.execute(
                """
                INSERT INTO artwork_generation_tasks (
                    task_id, task_version, request_json, request_hash, status,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'PENDING', ?, ?)
                """,
                (
                    request.task_id,
                    request.task_version,
                    request_json,
                    request_hash,
                    now,
                    now,
                ),
            )
            connection.commit()
        task = self.get(request.task_id, request.task_version)
        return task, True

    def get(self, task_id: int, task_version: int) -> Optional[ArtworkGenerationTask]:
        """작업 ID와 버전으로 저장 상태를 반환한다."""
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT * FROM artwork_generation_tasks
                WHERE task_id = ? AND task_version = ?
                """,
                (task_id, task_version),
            ).fetchone()
        return self._task_from_row(row) if row is not None else None

    def list_pending(self) -> list[ArtworkGenerationTask]:
        """실행을 기다리는 모든 작업을 생성 시각 순서로 반환한다."""
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM artwork_generation_tasks
                WHERE status = 'PENDING'
                ORDER BY created_at, task_id, task_version
                """
            ).fetchall()
        return [self._task_from_row(row) for row in rows]

    def claim(self, task_id: int, task_version: int) -> Optional[ArtworkGenerationTask]:
        """대기 작업 하나를 원자적으로 실행 중 상태로 전환한다."""
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                UPDATE artwork_generation_tasks
                SET status = 'RUNNING', updated_at = ?
                WHERE task_id = ? AND task_version = ? AND status = 'PENDING'
                """,
                (self._now(), task_id, task_version),
            )
            changed = connection.execute("SELECT changes()").fetchone()[0]
            row = connection.execute(
                """
                SELECT * FROM artwork_generation_tasks
                WHERE task_id = ? AND task_version = ?
                """,
                (task_id, task_version),
            ).fetchone()
            connection.commit()
        return self._task_from_row(row) if changed and row is not None else None

    def save_source(
        self, task_id: int, task_version: int, source: ArtworkSourceMetadata
    ) -> ArtworkSourceMetadata:
        """작업에 선택된 원본을 최초 한 번 저장해 재시작 후에도 유지한다."""
        source_json = json.dumps(
            source.model_dump(mode="json", by_alias=True),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                UPDATE artwork_generation_tasks
                SET source_json = COALESCE(source_json, ?), updated_at = ?
                WHERE task_id = ? AND task_version = ? AND status = 'RUNNING'
                """,
                (source_json, self._now(), task_id, task_version),
            )
            row = connection.execute(
                """
                SELECT source_json FROM artwork_generation_tasks
                WHERE task_id = ? AND task_version = ? AND status = 'RUNNING'
                """,
                (task_id, task_version),
            ).fetchone()
            if row is None:
                connection.rollback()
                raise RuntimeError("source can only be saved for a running task")
            connection.commit()
        return ArtworkSourceMetadata.model_validate_json(row["source_json"])

    def save_pending_image(
        self, task_id: int, task_version: int, image: ArtworkImageMetadata
    ) -> None:
        """업로드 전 이미지 정보를 저장해 업로드 중단 뒤 결과를 확인할 수 있게 한다."""
        image_json = json.dumps(
            image.model_dump(mode="json", by_alias=True),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE artwork_generation_tasks
                SET image_json = ?, updated_at = ?
                WHERE task_id = ? AND task_version = ? AND status = 'RUNNING'
                """,
                (image_json, self._now(), task_id, task_version),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("image metadata can only be saved for a running task")
            connection.commit()

    def clear_pending_image(self, task_id: int, task_version: int) -> None:
        """존재하지 않는 업로드 결과의 임시 메타데이터를 지운다."""
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE artwork_generation_tasks
                SET image_json = NULL, updated_at = ?
                WHERE task_id = ? AND task_version = ? AND status = 'RUNNING'
                """,
                (self._now(), task_id, task_version),
            )
            connection.commit()

    def mark_succeeded(
        self,
        task_id: int,
        task_version: int,
        image: ArtworkImageMetadata,
        source: ArtworkSourceMetadata,
        reuse_allowed: bool,
    ) -> None:
        """이미지 업로드가 끝난 작업의 결과 메타데이터를 저장한다."""
        image_json = json.dumps(
            image.model_dump(mode="json", by_alias=True), sort_keys=True, separators=(",", ":")
        )
        source_json = json.dumps(
            source.model_dump(mode="json", by_alias=True), sort_keys=True, separators=(",", ":")
        )
        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE artwork_generation_tasks
                SET status = 'SUCCEEDED', image_json = ?, source_json = ?,
                    reuse_allowed = ?, error_code = NULL, retryable = NULL, updated_at = ?
                WHERE task_id = ? AND task_version = ? AND status = 'RUNNING'
                """,
                (
                    image_json,
                    source_json,
                    int(reuse_allowed),
                    self._now(),
                    task_id,
                    task_version,
                ),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("only a running task can be marked successful")
            connection.commit()

    def mark_failed(
        self,
        task_id: int,
        task_version: int,
        error_code: str,
        retryable: bool,
    ) -> None:
        """실패 코드와 명시적 재시도 가능 여부를 저장한다."""
        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE artwork_generation_tasks
                SET status = 'FAILED', error_code = ?, retryable = ?, updated_at = ?
                WHERE task_id = ? AND task_version = ? AND status IN ('PENDING', 'RUNNING')
                """,
                (error_code, int(retryable), self._now(), task_id, task_version),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("only a pending or running task can be marked failed")
            connection.commit()

    def recover_interrupted(self) -> None:
        """프로세스 재시작 시 실행 중 상태를 대기로 되돌린다."""
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE artwork_generation_tasks
                SET status = 'PENDING', updated_at = ?
                WHERE status = 'RUNNING'
                """,
                (self._now(),),
            )
            connection.commit()

    @staticmethod
    def _task_from_row(row: sqlite3.Row) -> ArtworkGenerationTask:
        """SQLite 행을 타입이 지정된 작업으로 변환한다."""
        request = ArtworkGenerationRequest.model_validate_json(row["request_json"])
        source = (
            ArtworkSourceMetadata.model_validate_json(row["source_json"])
            if row["source_json"]
            else None
        )
        image = (
            ArtworkImageMetadata.model_validate_json(row["image_json"])
            if row["image_json"]
            else None
        )
        return ArtworkGenerationTask(
            request=request,
            status=row["status"],
            source=source,
            image=image,
            reuse_allowed=bool(row["reuse_allowed"])
            if row["reuse_allowed"] is not None
            else None,
            error_code=row["error_code"],
            retryable=bool(row["retryable"]) if row["retryable"] is not None else None,
        )
