"""저장된 명화 생성 작업을 백그라운드에서 실행한다."""

import logging
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Lock
from typing import Callable, Optional, Protocol

from moamu_ai.artwork_task_store import (
    ArtworkGenerationTask,
    ArtworkGenerationTaskStore,
)
from moamu_ai.errors import (
    ArtworkGenerationExpiredError,
    ArtworkSourceUnavailableError,
    ImageStoreConfigurationError,
    InvalidModelOutputError,
    ProviderConfigurationError,
)

logger = logging.getLogger(__name__)


class ArtworkTaskProcessor(Protocol):
    """저장된 한 건의 명화 생성 작업을 처리한다."""

    def process(self, task: ArtworkGenerationTask) -> None:
        """편집·업로드를 수행하고 성공 결과를 작업 저장소에 반영한다."""


ProcessorFactory = Callable[[], ArtworkTaskProcessor]


class ArtworkGenerationWorker:
    """SQLite 대기 작업을 단일 워커에서 순서대로 처리한다."""

    def __init__(
        self,
        task_store: ArtworkGenerationTaskStore,
        processor_factory: ProcessorFactory,
    ):
        """작업 저장소와 작업별 프로세서 팩토리를 보관한다."""
        self.task_store = task_store
        self.processor_factory = processor_factory
        self._executor: Optional[ThreadPoolExecutor] = None
        self._scheduled: set[tuple[int, int]] = set()
        self._lock = Lock()

    def start(self) -> None:
        """중단된 작업을 복구하고 대기 중인 작업 처리를 시작한다."""
        with self._lock:
            if self._executor is not None:
                return
            self._executor = ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix="moamu-artwork",
            )
        self.task_store.recover_interrupted()
        for task in self.task_store.list_pending():
            self.submit(task.request.task_id, task.request.task_version)

    def submit(self, task_id: int, task_version: int) -> None:
        """작업 키를 실행 큐에 한 번만 등록한다."""
        key = (task_id, task_version)
        with self._lock:
            executor = self._executor
            if executor is None:
                raise RuntimeError("artwork worker has not started")
            if key in self._scheduled:
                return
            self._scheduled.add(key)
            try:
                executor.submit(self._run, task_id, task_version)
            except Exception:
                self._scheduled.remove(key)
                raise

    def stop(self) -> None:
        """진행 중인 작업이 끝나면 워커 풀을 종료한다."""
        with self._lock:
            executor = self._executor
            self._executor = None
        if executor is not None:
            executor.shutdown(wait=True)

    def _run(self, task_id: int, task_version: int) -> None:
        """작업을 선점해 처리하고 계약된 최종 상태를 저장한다."""
        try:
            task = self.task_store.claim(task_id, task_version)
            if task is None:
                return
            if task.request.expires_at <= datetime.now(timezone.utc):
                raise ArtworkGenerationExpiredError("artwork generation task expired")
            self.processor_factory().process(task)
        except ArtworkGenerationExpiredError:
            self._mark_failed(task_id, task_version, "ARTWORK_TASK_EXPIRED", False)
        except (ArtworkSourceUnavailableError, ImageStoreConfigurationError,
                InvalidModelOutputError, ProviderConfigurationError):
            self._mark_failed(task_id, task_version, "ARTWORK_GENERATION_FAILED", False)
        except Exception as exc:
            cause = exc.__cause__
            provider_status_code = getattr(cause, "status_code", None)
            if not isinstance(provider_status_code, int):
                provider_status_code = getattr(cause, "code", None)
            if not isinstance(provider_status_code, int):
                provider_status_code = "unknown"
            logger.error(
                "artwork_generation_failed taskId=%s taskVersion=%s "
                "errorType=%s causeType=%s providerStatusCode=%s",
                task_id,
                task_version,
                type(exc).__name__,
                type(cause).__name__ if cause is not None else "unknown",
                provider_status_code,
            )
            self._mark_failed(task_id, task_version, "ARTWORK_GENERATION_FAILED", True)
        finally:
            with self._lock:
                self._scheduled.discard((task_id, task_version))

    def _mark_failed(
        self,
        task_id: int,
        task_version: int,
        error_code: str,
        retryable: bool,
    ) -> None:
        """실패 코드와 재시도 가능 여부를 저장한다."""
        try:
            self.task_store.mark_failed(task_id, task_version, error_code, retryable)
        except (OSError, RuntimeError, sqlite3.Error) as exc:
            logger.error(
                "artwork_generation_failure_state_unavailable "
                "taskId=%s taskVersion=%s errorType=%s",
                task_id,
                task_version,
                type(exc).__name__,
            )
