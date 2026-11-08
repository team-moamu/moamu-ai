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
    def open_image(self, image_key: str) -> AbstractContextManager[Path]:
        """Yield a local file path for the duration of an inference call."""


class LocalImageStore:
    def __init__(self, image_root: Path):
        self.image_root = image_root

    @contextmanager
    def open_image(self, image_key: str) -> Iterator[Path]:
        try:
            image_path = resolve_image_path(image_key, self.image_root)
        except (ImageNotFoundError, ImagePathNotAllowedError, ImageUnreadableError) as exc:
            raise ImageFetchFailedError("image object could not be fetched") from exc
        except ImageRootUnavailableError as exc:
            raise ImageStoreConfigurationError("local image root is unavailable") from exc
        yield image_path


class S3ImageStore:
    def __init__(self, bucket: str, client=None):
        if not bucket:
            raise ImageStoreConfigurationError("S3_BUCKET is not configured")
        self.bucket = bucket
        self.client = client

    @contextmanager
    def open_image(self, image_key: str) -> Iterator[Path]:
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
    if settings.ai_image_source == "local":
        return LocalImageStore(settings.ai_image_root)
    if settings.ai_image_source != "s3":
        raise ImageStoreConfigurationError("AI_IMAGE_SOURCE is not supported")
    if not settings.s3_bucket:
        raise ImageStoreConfigurationError("S3_BUCKET is not configured")

    access_key = settings.s3_access_key_id
    secret_key = settings.s3_secret_access_key
    if bool(access_key) != bool(secret_key):
        raise ImageStoreConfigurationError(
            "S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY must be configured together"
        )

    try:
        import boto3

        client_kwargs = {"region_name": settings.aws_region}
        if access_key and secret_key:
            client_kwargs.update(
                aws_access_key_id=access_key.get_secret_value(),
                aws_secret_access_key=secret_key.get_secret_value(),
            )
        client = boto3.client("s3", **client_kwargs)
    except Exception as exc:
        raise ImageStoreConfigurationError("S3 client could not be configured") from exc
    return S3ImageStore(bucket=settings.s3_bucket, client=client)
