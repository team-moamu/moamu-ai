import shutil
import tempfile
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path, PurePosixPath
from typing import Protocol

from moamu_ai.errors import (
    ImageFetchFailedError,
    ImageNotFoundError,
    ImagePathNotAllowedError,
    ImageRootUnavailableError,
    ImageStoreConfigurationError,
    ImageUnreadableError,
)
from moamu_ai.image_paths import resolve_image_path


class ImageStore(Protocol):
    """이미지 저장소 구현체가 따라야 하는 인터페이스."""

    def open_image(self, image_key: str) -> AbstractContextManager[Path]:
        """추론 중 사용할 로컬 이미지 경로를 제공한다.

        Args:
            image_key: 이미지 저장소에서 사용하는 키 또는 경로.

        Returns:
            사용 후 정리되는 로컬 파일 경로 컨텍스트 관리자.
        """


class LocalImageStore:
    """허용된 로컬 디렉터리에서 이미지를 제공하는 저장소."""

    def __init__(self, image_root: Path):
        """지정한 로컬 디렉터리를 이미지 저장소로 설정한다."""
        self.image_root = image_root

    @contextmanager
    def open_image(self, image_key: str) -> Iterator[Path]:
        """로컬 이미지 경로를 검증한 뒤 컨텍스트 안에서 제공한다."""
        try:
            image_path = resolve_image_path(image_key, self.image_root)
        except (ImageNotFoundError, ImagePathNotAllowedError, ImageUnreadableError) as exc:
            raise ImageFetchFailedError("image object could not be fetched") from exc
        except ImageRootUnavailableError as exc:
            raise ImageStoreConfigurationError("local image root is unavailable") from exc
        yield image_path


class S3ImageStore:
    """S3 객체를 임시 파일로 제공하는 이미지 저장소."""

    def __init__(self, bucket: str, client=None):
        """S3 버킷과 클라이언트로 이미지 저장소를 구성한다."""
        if not bucket:
            raise ImageStoreConfigurationError("S3_BUCKET is not configured")
        self.bucket = bucket
        self.client = client

    @contextmanager
    def open_image(self, image_key: str) -> Iterator[Path]:
        """S3 객체를 임시 파일로 내려받아 사용 후 정리한다."""
        if self.client is None:
            raise ImageStoreConfigurationError("S3 client is not configured")

        body = None
        temporary_path = None
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=image_key)
            body = response["Body"]
            with tempfile.NamedTemporaryFile(
                prefix="moamu-photo-",
                suffix=PurePosixPath(image_key).suffix,
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                shutil.copyfileobj(body, temporary_file)
        except Exception as exc:
            if body is not None:
                try:
                    body.close()
                except Exception:
                    pass
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise ImageFetchFailedError("image object could not be fetched") from exc

        try:
            yield temporary_path
        finally:
            try:
                body.close()
            except Exception:
                pass
            finally:
                temporary_path.unlink(missing_ok=True)


def create_image_store(settings) -> ImageStore:
    """설정에 지정된 로컬 또는 S3 이미지 저장소를 생성한다.

    Args:
        settings: 이미지 소스와 자격 증명이 담긴 앱 설정.

    Returns:
        선택된 이미지 저장소 구현체.

    Raises:
        ImageStoreConfigurationError: 저장소 종류나 필수 설정이 올바르지 않은 경우.
    """
    if settings.ai_image_source == "local":
        return LocalImageStore(settings.ai_image_root)
    if settings.ai_image_source != "s3":
        raise ImageStoreConfigurationError("AI_IMAGE_SOURCE is not supported")
    if not settings.s3_bucket:
        raise ImageStoreConfigurationError("S3_BUCKET is not configured")

    access_key = settings.s3_access_key_id
    secret_key = settings.s3_secret_access_key
    session_token = settings.s3_session_token
    if bool(access_key) != bool(secret_key):
        raise ImageStoreConfigurationError(
            "S3/AWS access key ID and secret access key must be configured together"
        )
    if session_token and not (access_key and secret_key):
        raise ImageStoreConfigurationError(
            "S3/AWS session token requires access key credentials"
        )

    try:
        import boto3

        client_kwargs = {"region_name": settings.aws_region}
        if access_key and secret_key:
            client_kwargs.update(
                aws_access_key_id=access_key.get_secret_value(),
                aws_secret_access_key=secret_key.get_secret_value(),
            )
            if session_token:
                client_kwargs["aws_session_token"] = session_token.get_secret_value()
        client = boto3.client("s3", **client_kwargs)
    except Exception as exc:
        raise ImageStoreConfigurationError("S3 client could not be configured") from exc
    return S3ImageStore(bucket=settings.s3_bucket, client=client)
