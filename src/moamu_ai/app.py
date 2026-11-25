import logging
import secrets
import sqlite3
from threading import Lock
from typing import Annotated, Optional

from fastapi import Depends, FastAPI, Request
from fastapi import Path as PathParam
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from moamu_ai.artwork_generation_service import ArtworkGenerationProcessor, ArtworkImageStorage
from moamu_ai.artwork_generation_worker import ArtworkGenerationWorker
from moamu_ai.artwork_task_store import (
    ArtworkGenerationTaskStore,
    ArtworkTaskExpiredError,
    ArtworkTaskPayloadConflictError,
)
from moamu_ai.config import Settings
from moamu_ai.errors import (
    ImageFetchFailedError,
    ImageStoreConfigurationError,
    InvalidModelOutputError,
    ModelProviderError,
    ProviderConfigurationError,
    UnsupportedImageError,
)
from moamu_ai.goal_service import GoalVerifiabilityService
from moamu_ai.image_sources import ImageStore, S3ImageStore, create_image_store
from moamu_ai.providers.base import ArtworkEditor, GoalAnalyzer, PhotoJudge
from moamu_ai.providers.factory import (
    create_artwork_editor,
    create_goal_analyzer,
    create_photo_judge,
)
from moamu_ai.schemas import (
    ArtworkGenerationErrorResponse,
    ArtworkGenerationRequest,
    ArtworkGenerationResponse,
    GoalAnalysisErrorResponse,
    GoalVerifiabilityRequest,
    GoalVerifiabilityResponse,
    PhotoVerificationErrorResponse,
    PhotoVerificationRequest,
    PhotoVerificationResponse,
)
from moamu_ai.service import PhotoVerificationService

logger = logging.getLogger(__name__)


class ArtworkAPIError(Exception):
    """명화 생성 API의 HTTP 상태와 계약 오류를 보관한다."""

    def __init__(self, status_code: int, code: str, message: str):
        """응답 상태와 공개 오류 문구를 저장한다."""
        self.status_code = status_code
        self.code = code
        self.message = message


def create_app(
    settings: Optional[Settings] = None,
    judge: Optional[PhotoJudge] = None,
    image_store: Optional[ImageStore] = None,
    goal_analyzer: Optional[GoalAnalyzer] = None,
    artwork_editor: Optional[ArtworkEditor] = None,
    artwork_image_storage: Optional[ArtworkImageStorage] = None,
    artwork_task_store: Optional[ArtworkGenerationTaskStore] = None,
) -> FastAPI:
    """사진 인증 API 애플리케이션을 구성한다.

    Args:
        settings: 앱에서 사용할 설정. 생략하면 환경 변수에서 읽는다.
        judge: 주입할 판정 모델. 생략하면 첫 요청 때 생성한다.
        image_store: 주입할 이미지 저장소. 생략하면 설정에 따라 생성한다.
        goal_analyzer: 주입할 자유목표 분석기. 생략하면 첫 요청 때 생성한다.
        artwork_editor: 주입할 명화 편집기. 생략하면 첫 작업 때 생성한다.
        artwork_image_storage: 주입할 명화 입력·출력 저장소. 생략하면 S3를 사용한다.
        artwork_task_store: 주입할 작업 저장소. 생략하면 설정한 SQLite 파일을 사용한다.

    Returns:
        상태 확인, 사진 판정, 목표 분석 및 명화 생성 경로가 등록된 FastAPI 앱.
    """
    configured_settings = settings or Settings()
    app = FastAPI(
        title="MOAMU AI Photo Verification",
        version="0.2.0",
        description="Internal per-condition photo verification endpoint.",
    )
    app.state.settings = configured_settings
    app.state.judge = judge
    app.state.image_store = image_store
    app.state.goal_analyzer = goal_analyzer
    app.state.artwork_editor = artwork_editor
    app.state.artwork_image_storage = artwork_image_storage
    app.state.artwork_task_store = artwork_task_store
    app.state.artwork_worker = None
    app.state.provider_lock = Lock()
    app.state.goal_provider_lock = Lock()
    app.state.image_store_lock = Lock()
    app.state.artwork_provider_lock = Lock()
    artwork_bearer = HTTPBearer(auto_error=False)

    def get_judge() -> PhotoJudge:
        """판정 모델을 필요할 때 한 번 생성해 반환한다."""
        active_judge = app.state.judge
        if active_judge is not None:
            return active_judge
        with app.state.provider_lock:
            active_judge = app.state.judge
            if active_judge is None:
                active_judge = create_photo_judge(app.state.settings)
                app.state.judge = active_judge
        return active_judge

    def get_goal_analyzer() -> GoalAnalyzer:
        """목표 분석기를 필요할 때 한 번 생성해 반환한다."""
        active_analyzer = app.state.goal_analyzer
        if active_analyzer is not None:
            return active_analyzer
        with app.state.goal_provider_lock:
            active_analyzer = app.state.goal_analyzer
            if active_analyzer is None:
                active_analyzer = create_goal_analyzer(app.state.settings)
                app.state.goal_analyzer = active_analyzer
        return active_analyzer

    def get_image_store() -> ImageStore:
        """이미지 저장소를 필요할 때 한 번 생성해 반환한다."""
        active_store = app.state.image_store
        if active_store is not None:
            return active_store
        with app.state.image_store_lock:
            active_store = app.state.image_store
            if active_store is None:
                active_store = create_image_store(app.state.settings)
                app.state.image_store = active_store
        return active_store

    def get_artwork_editor() -> ArtworkEditor:
        """Gemini 명화 편집기를 필요할 때 한 번 생성해 반환한다."""
        active_editor = app.state.artwork_editor
        if active_editor is not None:
            return active_editor
        with app.state.artwork_provider_lock:
            active_editor = app.state.artwork_editor
            if active_editor is None:
                active_editor = create_artwork_editor(app.state.settings)
                app.state.artwork_editor = active_editor
        return active_editor

    def get_artwork_task_store() -> ArtworkGenerationTaskStore:
        """설정한 SQLite 파일을 사용하는 작업 저장소를 반환한다."""
        active_store = app.state.artwork_task_store
        if active_store is None:
            active_store = ArtworkGenerationTaskStore(
                app.state.settings.ai_artwork_task_db_path
            )
            app.state.artwork_task_store = active_store
        return active_store

    def create_artwork_processor() -> ArtworkGenerationProcessor:
        """Gemini 편집기와 S3를 연결한 작업 처리기를 만든다."""
        active_storage = app.state.artwork_image_storage
        if active_storage is None:
            configured_storage = get_image_store()
            if not isinstance(configured_storage, S3ImageStore):
                raise ImageStoreConfigurationError(
                    "artwork generation requires an S3 image store"
                )
            active_storage = configured_storage
        return ArtworkGenerationProcessor(
            get_artwork_task_store(),
            active_storage,
            get_artwork_editor(),
        )

    def start_artwork_worker() -> None:
        """저장된 대기 작업을 복구하는 단일 백그라운드 워커를 시작한다."""
        worker = ArtworkGenerationWorker(
            get_artwork_task_store(),
            create_artwork_processor,
        )
        worker.start()
        app.state.artwork_worker = worker

    def stop_artwork_worker() -> None:
        """애플리케이션 종료 전에 워커를 정리한다."""
        worker = app.state.artwork_worker
        if worker is not None:
            worker.stop()
            app.state.artwork_worker = None

    def require_artwork_auth(
        credentials: Annotated[
            Optional[HTTPAuthorizationCredentials], Depends(artwork_bearer)
        ],
    ) -> None:
        """설정된 내부 Bearer 토큰이 일치하는지 확인한다."""
        configured_token = app.state.settings.ai_internal_api_token
        if configured_token is None or not configured_token.get_secret_value():
            raise ArtworkAPIError(
                503,
                "INTERNAL_AUTH_NOT_CONFIGURED",
                "내부 명화 생성 API 인증이 설정되지 않았습니다.",
            )
        if credentials is None or not secrets.compare_digest(
            credentials.credentials.encode("utf-8"),
            configured_token.get_secret_value().encode("utf-8"),
        ):
            raise ArtworkAPIError(401, "UNAUTHORIZED", "내부 API 인증이 필요합니다.")

    app.router.add_event_handler("startup", start_artwork_worker)
    app.router.add_event_handler("shutdown", stop_artwork_worker)

    @app.exception_handler(RequestValidationError)
    async def invalid_request_handler(request: Request, _exc: RequestValidationError):
        """요청 검증 오류를 백엔드 공통 오류 응답으로 변환한다."""
        if request.url.path.startswith("/internal/artwork-generations"):
            return _artwork_error_response(
                status_code=400,
                code="INVALID_REQUEST",
                message="요청 형식 또는 필수 값이 올바르지 않습니다.",
            )
        if request.url.path == "/internal/goals/evaluate-verifiability":
            return _goal_error_response(
                status_code=400,
                code="INVALID_REQUEST",
                message="요청이 올바르지 않습니다.",
            )
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        return _error_response(
            status_code=400,
            code="INVALID_REQUEST",
            message="요청 형식 또는 필수 값이 올바르지 않습니다.",
            ai_task_id=_request_id(payload, "ai_task_id"),
            verification_id=_request_id(payload, "verification_id"),
        )

    @app.exception_handler(ArtworkAPIError)
    async def artwork_api_error_handler(_request: Request, exc: ArtworkAPIError):
        """명화 생성 API 오류를 공통 응답 형식으로 직렬화한다."""
        return _artwork_error_response(exc.status_code, exc.code, exc.message)

    @app.get("/healthz", tags=["health"])
    def health_check():
        """서버 상태 확인 요청에 정상 상태를 반환한다."""
        return {"status": "ok"}

    @app.post(
        "/internal/artwork-generations",
        response_model=ArtworkGenerationResponse,
        status_code=202,
        tags=["internal artwork generation"],
        summary="Accept a public-domain artwork edit task",
        responses={
            400: {"model": ArtworkGenerationErrorResponse, "description": "Invalid request"},
            401: {"model": ArtworkGenerationErrorResponse, "description": "Unauthorized"},
            409: {"model": ArtworkGenerationErrorResponse, "description": "Task payload conflict"},
            503: {
                "model": ArtworkGenerationErrorResponse,
                "description": "Authentication, task storage, or worker unavailable",
            },
        },
    )
    def accept_artwork_generation(
        payload: ArtworkGenerationRequest,
        _auth: None = Depends(require_artwork_auth),
    ):
        """작업을 영속 저장한 뒤 `202 PENDING`을 반환한다."""
        worker = app.state.artwork_worker
        if worker is None:
            raise ArtworkAPIError(
                503,
                "ARTWORK_WORKER_UNAVAILABLE",
                "명화 생성 작업 처리를 시작할 수 없습니다.",
            )
        try:
            task, _created = get_artwork_task_store().accept(payload)
        except ArtworkTaskExpiredError as exc:
            raise ArtworkAPIError(
                400,
                "INVALID_REQUEST",
                "이미 만료된 생성 작업은 접수할 수 없습니다.",
            ) from exc
        except ArtworkTaskPayloadConflictError as exc:
            raise ArtworkAPIError(
                409,
                "ARTWORK_TASK_PAYLOAD_CONFLICT",
                "같은 작업 ID와 버전에 이미 다른 요청이 접수되었습니다.",
            ) from exc
        except (OSError, sqlite3.Error) as exc:
            logger.error(
                "artwork_task_store_failed operation=accept errorType=%s",
                type(exc).__name__,
            )
            raise ArtworkAPIError(
                503,
                "ARTWORK_TASK_STORE_UNAVAILABLE",
                "명화 생성 작업 저장소에 접근할 수 없습니다.",
            ) from exc

        if task.status == "PENDING":
            try:
                worker.submit(payload.task_id, payload.task_version)
            except RuntimeError as exc:
                raise ArtworkAPIError(
                    503,
                    "ARTWORK_WORKER_UNAVAILABLE",
                    "명화 생성 작업 처리를 시작할 수 없습니다.",
                ) from exc
        return task.to_response()

    @app.get(
        "/internal/artwork-generations/{taskId}/versions/{taskVersion}",
        response_model=ArtworkGenerationResponse,
        tags=["internal artwork generation"],
        summary="Get an artwork generation task status",
        responses={
            400: {"model": ArtworkGenerationErrorResponse, "description": "Invalid path"},
            401: {"model": ArtworkGenerationErrorResponse, "description": "Unauthorized"},
            404: {"model": ArtworkGenerationErrorResponse, "description": "Task not found"},
            503: {
                "model": ArtworkGenerationErrorResponse,
                "description": "Authentication or task storage is unavailable",
            },
        },
    )
    def get_artwork_generation_status(
        task_id: int = PathParam(alias="taskId", gt=0),
        task_version: int = PathParam(alias="taskVersion", gt=0),
        _auth: None = Depends(require_artwork_auth),
    ):
        """작업 버전의 저장된 현재 상태나 최종 결과를 반환한다."""
        try:
            task = get_artwork_task_store().get(task_id, task_version)
        except (OSError, sqlite3.Error) as exc:
            logger.error(
                "artwork_task_store_failed operation=get errorType=%s",
                type(exc).__name__,
            )
            raise ArtworkAPIError(
                503,
                "ARTWORK_TASK_STORE_UNAVAILABLE",
                "명화 생성 작업 저장소에 접근할 수 없습니다.",
            ) from exc
        if task is None:
            raise ArtworkAPIError(
                404,
                "ARTWORK_TASK_VERSION_NOT_FOUND",
                "요청한 작업 또는 버전을 찾을 수 없습니다.",
            )
        return task.to_response()

    @app.post(
        "/internal/photo-verifications",
        response_model=PhotoVerificationResponse,
        tags=["internal photo verification"],
        summary="Evaluate an S3 photo against supplied challenge conditions",
        responses={
            400: {"model": PhotoVerificationErrorResponse, "description": "Invalid request"},
            422: {
                "model": PhotoVerificationErrorResponse,
                "description": "Unsupported image or image fetch failed",
            },
            500: {
                "model": PhotoVerificationErrorResponse,
                "description": "Internal AI server error",
            },
            503: {
                "model": PhotoVerificationErrorResponse,
                "description": "AI model temporarily unavailable",
            },
        },
    )
    def verify_photo(payload: PhotoVerificationRequest):
        """전달된 이미지와 조건을 판정하고 계약 형식으로 응답한다."""
        try:
            service = PhotoVerificationService(
                get_judge,
                get_image_store(),
                model_version=app.state.settings.ai_model_version,
            )
            return service.verify(payload)
        except UnsupportedImageError:
            return _error_response(
                status_code=422,
                code="UNSUPPORTED_IMAGE",
                message="지원하지 않는 이미지입니다.",
                ai_task_id=payload.ai_task_id,
                verification_id=payload.verification_id,
            )
        except ImageFetchFailedError:
            return _error_response(
                status_code=422,
                code="IMAGE_FETCH_FAILED",
                message="S3 인증 사진을 조회할 수 없습니다.",
                ai_task_id=payload.ai_task_id,
                verification_id=payload.verification_id,
            )
        except ImageStoreConfigurationError:
            logger.error("photo_verification_error code=INTERNAL_ERROR component=image_store")
            return _error_response(
                status_code=500,
                code="INTERNAL_ERROR",
                message="AI 서버 내부 오류가 발생했습니다.",
                ai_task_id=payload.ai_task_id,
                verification_id=payload.verification_id,
            )
        except (ProviderConfigurationError, ModelProviderError, InvalidModelOutputError):
            logger.warning("photo_verification_error code=MODEL_UNAVAILABLE")
            return _error_response(
                status_code=503,
                code="MODEL_UNAVAILABLE",
                message="현재 판정 모델을 사용할 수 없습니다.",
                ai_task_id=payload.ai_task_id,
                verification_id=payload.verification_id,
            )
        except Exception:
            logger.exception("photo_verification_error code=INTERNAL_ERROR")
            return _error_response(
                status_code=500,
                code="INTERNAL_ERROR",
                message="AI 서버 내부 오류가 발생했습니다.",
                ai_task_id=payload.ai_task_id,
                verification_id=payload.verification_id,
            )

    @app.post(
        "/internal/goals/evaluate-verifiability",
        response_model=GoalVerifiabilityResponse,
        tags=["internal goal analysis"],
        summary="Evaluate whether a user goal can be verified from a photo",
        responses={
            400: {
                "model": GoalAnalysisErrorResponse,
                "description": "Invalid request",
            },
            500: {
                "model": GoalAnalysisErrorResponse,
                "description": "Internal AI server error",
            },
            503: {
                "model": GoalAnalysisErrorResponse,
                "description": "AI model temporarily unavailable",
            },
        },
    )
    def evaluate_goal(payload: GoalVerifiabilityRequest):
        """자유목표의 사진 인증 가능 여부와 안내를 반환한다."""
        try:
            return GoalVerifiabilityService(get_goal_analyzer()).evaluate(payload)
        except (ProviderConfigurationError, ModelProviderError, InvalidModelOutputError):
            logger.warning("goal_analysis_error code=AI_MODEL_UNAVAILABLE")
            return _goal_error_response(
                status_code=503,
                code="AI_MODEL_UNAVAILABLE",
                message="AI 모델을 일시적으로 사용할 수 없습니다.",
            )
        except Exception:
            logger.exception("goal_analysis_error code=INTERNAL_SERVER_ERROR")
            return _goal_error_response(
                status_code=500,
                code="INTERNAL_SERVER_ERROR",
                message="사진 인증 가능 여부를 판정하는 중 오류가 발생했습니다.",
            )

    return app


def _request_id(payload, field: str) -> Optional[str]:
    """오류 응답에 넣을 수 있는 요청 식별자를 안전하게 추출한다.

    Args:
        payload: 요청 본문으로 읽은 값.
        field: 추출할 식별자 필드명.

    Returns:
        길이 제한을 만족하는 문자열 식별자. 없으면 ``None``.
    """
    if isinstance(payload, dict):
        value = payload.get(field)
        if isinstance(value, str) and value and len(value) <= 100:
            return value
    return None


def _error_response(
    status_code: int,
    code: str,
    message: str,
    ai_task_id: Optional[str],
    verification_id: Optional[str],
) -> JSONResponse:
    """API 오류 내용을 공통 응답 스키마로 직렬화한다.

    Args:
        status_code: HTTP 상태 코드.
        code: 백엔드 계약에 정의된 오류 코드.
        message: 응답에 포함할 오류 메시지.
        ai_task_id: 원 요청의 작업 식별자.
        verification_id: 원 요청의 인증 식별자.

    Returns:
        공통 오류 본문을 담은 JSON 응답.
    """
    body = PhotoVerificationErrorResponse.model_validate(
        {
            "ai_task_id": ai_task_id,
            "verification_id": verification_id,
            "processing_status": "ERROR",
            "error": {"code": code, "message": message},
        }
    )
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(mode="json"),
    )


def _goal_error_response(
    status_code: int,
    code: str,
    message: str,
) -> JSONResponse:
    """자유목표 API 오류를 전용 응답 형식으로 직렬화한다."""
    body = GoalAnalysisErrorResponse.model_validate({"code": code, "message": message})
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


def _artwork_error_response(
    status_code: int,
    code: str,
    message: str,
) -> JSONResponse:
    """명화 생성 내부 API 오류를 계약 형식으로 직렬화한다."""
    body = ArtworkGenerationErrorResponse.model_validate(
        {"success": False, "error": {"code": code, "message": message}}
    )
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


app = create_app()
