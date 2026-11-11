import sys
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from moamu_ai.config import Settings
from moamu_ai.errors import ImageFetchFailedError, ImageStoreConfigurationError
from moamu_ai.image_sources import LocalImageStore, S3ImageStore, create_image_store


def test_local_image_store_resolves_key_under_configured_root(tmp_path: Path):
    """로컬 저장소가 이미지 키를 설정 루트에서 찾는지 확인한다."""
    root = tmp_path / "images"
    root.mkdir()
    image = root / "proof.jpg"
    image.write_bytes(b"image bytes")

    with LocalImageStore(root).open_image("proof.jpg") as resolved:
        assert resolved == image.resolve()


def test_s3_image_store_downloads_key_to_temporary_file_and_cleans_it():
    """S3 객체를 임시 파일로 제공하고 종료 후 지우는지 확인한다."""
    body = BytesIO(b"s3-image-bytes")
    seen = {}

    class FakeS3Client:
        """정상 S3 객체 응답을 제공하는 테스트 클라이언트."""

        def get_object(self, **kwargs):
            """요청된 S3 키에 해당하는 테스트 객체를 반환한다."""
            seen.update(kwargs)
            return {"Body": body}

    store = S3ImageStore(bucket="bucket", client=FakeS3Client())
    temp_path = None
    with store.open_image("verifications/proof.jpg") as image_path:
        temp_path = image_path
        assert image_path.read_bytes() == b"s3-image-bytes"
        assert image_path.suffix == ".jpg"

    assert seen == {"Bucket": "bucket", "Key": "verifications/proof.jpg"}
    assert body.closed
    assert temp_path is not None and not temp_path.exists()


def test_s3_image_store_maps_fetch_failures_to_contract_error():
    """S3 조회 실패가 계약 오류로 변환되는지 확인한다."""
    class FailingS3Client:
        """S3 객체 조회 실패를 재현하는 테스트 클라이언트."""

        def get_object(self, **kwargs):
            """테스트용 S3 객체 조회 예외를 발생시킨다."""
            raise RuntimeError("private AWS detail")

    with pytest.raises(ImageFetchFailedError, match="could not be fetched"):
        with S3ImageStore(bucket="bucket", client=FailingS3Client()).open_image("proof.jpg"):
            pass


def test_create_image_store_passes_explicit_aws_credentials_and_session_token(monkeypatch):
    """S3 클라이언트 생성 시 키와 임시 세션 토큰을 boto3에 전달한다."""
    calls = {}

    def fake_client(service_name, **kwargs):
        calls["service_name"] = service_name
        calls["kwargs"] = kwargs
        return object()

    monkeypatch.setitem(sys.modules, "boto3", SimpleNamespace(client=fake_client))
    settings = Settings(
        _env_file=None,
        ai_image_source="s3",
        s3_bucket="test-bucket",
        aws_region="ap-northeast-2",
        s3_access_key_id=SecretStr("test-access-key"),
        s3_secret_access_key=SecretStr("test-secret-key"),
        s3_session_token=SecretStr("test-session-token"),
    )

    store = create_image_store(settings)

    assert isinstance(store, S3ImageStore)
    assert store.bucket == "test-bucket"
    assert calls == {
        "service_name": "s3",
        "kwargs": {
            "region_name": "ap-northeast-2",
            "aws_access_key_id": "test-access-key",
            "aws_secret_access_key": "test-secret-key",
            "aws_session_token": "test-session-token",
        },
    }


def test_create_image_store_rejects_incomplete_explicit_credentials(monkeypatch):
    """액세스 키 또는 시크릿 키 한쪽만 있으면 S3 클라이언트를 만들지 않는다."""
    settings = Settings(
        _env_file=None,
        ai_image_source="s3",
        s3_bucket="test-bucket",
        s3_access_key_id=SecretStr("test-access-key"),
    )

    with pytest.raises(ImageStoreConfigurationError, match="configured together"):
        create_image_store(settings)


def test_create_image_store_rejects_session_token_without_explicit_credentials():
    """명시적 키 쌍 없이 세션 토큰만 설정하는 경우 오류로 처리한다."""
    settings = Settings(
        _env_file=None,
        ai_image_source="s3",
        s3_bucket="test-bucket",
        s3_session_token=SecretStr("test-session-token"),
    )

    with pytest.raises(ImageStoreConfigurationError, match="requires access key credentials"):
        create_image_store(settings)
