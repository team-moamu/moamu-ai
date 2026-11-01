import logging
from threading import Lock
from typing import Optional

from fastapi import FastAPI, HTTPException

from moamu_ai.config import Settings
from moamu_ai.errors import (
    ImageNotFoundError,
    ImagePathNotAllowedError,
    ImageRootUnavailableError,
    ImageUnreadableError,
    InvalidModelOutputError,
    ModelProviderError,
    ProviderConfigurationError,
)
from moamu_ai.providers.base import PhotoJudge
from moamu_ai.providers.factory import create_photo_judge
from moamu_ai.schemas import PhotoVerificationRequest, PhotoVerificationResponse
from moamu_ai.service import PhotoVerificationService

logger = logging.getLogger(__name__)


def create_app(
    settings: Optional[Settings] = None,
    judge: Optional[PhotoJudge] = None,
) -> FastAPI:
    configured_settings = settings or Settings()
    app = FastAPI(
        title="MOAMU AI Photo Verification",
        version="0.1.0",
        description="Internal per-condition photo verification endpoint.",
    )
    app.state.settings = configured_settings
    app.state.judge = judge
    app.state.provider_lock = Lock()

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

    @app.get("/healthz", tags=["health"])
    def health_check():
        return {"status": "ok"}

    @app.post(
        "/internal/photo-verifications",
        response_model=PhotoVerificationResponse,
        tags=["internal photo verification"],
        summary="Evaluate a photo against frozen challenge conditions",
    )
    def verify_photo(payload: PhotoVerificationRequest) -> PhotoVerificationResponse:
        try:
            return PhotoVerificationService(
                get_judge,
                app.state.settings.ai_image_root,
            ).verify(payload)
        except ImageNotFoundError as exc:
            raise _api_error(404, "IMAGE_NOT_FOUND", str(exc)) from exc
        except ImagePathNotAllowedError as exc:
            raise _api_error(403, "IMAGE_PATH_NOT_ALLOWED", str(exc)) from exc
        except ImageRootUnavailableError as exc:
            raise _api_error(503, "IMAGE_ROOT_UNAVAILABLE", str(exc)) from exc
        except ImageUnreadableError as exc:
            raise _api_error(422, "IMAGE_NOT_READABLE", str(exc)) from exc
        except ProviderConfigurationError as exc:
            raise _api_error(503, "AI_PROVIDER_NOT_CONFIGURED", str(exc)) from exc
        except InvalidModelOutputError as exc:
            logger.warning("photo_verification_error code=INVALID_MODEL_OUTPUT")
            raise _api_error(
                502,
                "INVALID_MODEL_OUTPUT",
                "AI provider returned an invalid result",
            ) from exc
        except ModelProviderError as exc:
            logger.warning("photo_verification_error code=AI_PROVIDER_ERROR")
            raise _api_error(
                503,
                "AI_PROVIDER_ERROR",
                "AI provider is temporarily unavailable",
            ) from exc

    return app


def _api_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


app = create_app()
