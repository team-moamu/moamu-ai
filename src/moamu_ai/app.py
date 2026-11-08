import logging
from threading import Lock
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from moamu_ai.config import Settings
from moamu_ai.errors import (
    ImageFetchFailedError,
    ImageStoreConfigurationError,
    InvalidModelOutputError,
    ModelProviderError,
    ProviderConfigurationError,
    UnsupportedImageError,
)
from moamu_ai.image_sources import ImageStore, create_image_store
from moamu_ai.providers.base import PhotoJudge
from moamu_ai.providers.factory import create_photo_judge
from moamu_ai.schemas import (
    PhotoVerificationErrorResponse,
    PhotoVerificationRequest,
    PhotoVerificationResponse,
)
from moamu_ai.service import PhotoVerificationService

logger = logging.getLogger(__name__)


def create_app(
    settings: Optional[Settings] = None,
    judge: Optional[PhotoJudge] = None,
    image_store: Optional[ImageStore] = None,
) -> FastAPI:
    configured_settings = settings or Settings()
    app = FastAPI(
        title="MOAMU AI Photo Verification",
        version="0.2.0",
        description="Internal per-condition photo verification endpoint.",
    )
    app.state.settings = configured_settings
    app.state.judge = judge
    app.state.image_store = image_store
    app.state.provider_lock = Lock()
    app.state.image_store_lock = Lock()

    def get_judge() -> PhotoJudge:
        active_judge = app.state.judge
        if active_judge is not None:
            return active_judge
        with app.state.provider_lock:
            active_judge = app.state.judge
            if active_judge is None:
                active_judge = create_photo_judge(app.state.settings)
                app.state.judge = active_judge
        return active_judge

    def get_image_store() -> ImageStore:
        active_store = app.state.image_store
        if active_store is not None:
            return active_store
        with app.state.image_store_lock:
            active_store = app.state.image_store
            if active_store is None:
                active_store = create_image_store(app.state.settings)
                app.state.image_store = active_store
        return active_store

    @app.exception_handler(RequestValidationError)
    async def invalid_request_handler(request: Request, _exc: RequestValidationError):
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

    @app.get("/healthz", tags=["health"])
    def health_check():
        return {"status": "ok"}

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

    return app


def _request_id(payload, field: str) -> Optional[str]:
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


app = create_app()
